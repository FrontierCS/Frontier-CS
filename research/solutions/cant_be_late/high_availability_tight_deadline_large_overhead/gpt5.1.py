from typing import Any, List, Tuple

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.args = args
        self._cached_slack: float = -1.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could parse spec_path here for configuration.
        return self

    def _compute_progress(self) -> float:
        """Compute total task progress in seconds from task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if segments is None:
            return 0.0
        try:
            n = len(segments)
        except TypeError:
            return 0.0
        if n == 0:
            return 0.0

        first = segments[0]
        total = 0.0

        if isinstance(first, (int, float)):
            for v in segments:
                try:
                    total += float(v)
                except (TypeError, ValueError):
                    continue
        elif isinstance(first, (list, tuple)) and len(first) >= 2:
            for seg in segments:
                try:
                    start = float(seg[0])
                    end = float(seg[1])
                    total += max(0.0, end - start)
                except (TypeError, ValueError, IndexError):
                    continue
        else:
            for v in segments:
                try:
                    total += float(v)
                except (TypeError, ValueError):
                    continue

        if total < 0.0:
            total = 0.0
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Basic environment parameters
        elapsed = float(self.env.elapsed_seconds)
        dt = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        task_duration = float(self.task_duration)
        restart_oh = float(self.restart_overhead)

        # If task duration is non-positive, nothing to run.
        if task_duration <= 0.0:
            return ClusterType.NONE

        # Compute progress and remaining work/time.
        progress = self._compute_progress()
        if progress < 0.0:
            progress = 0.0
        if progress > task_duration:
            progress = task_duration

        remaining_task = task_duration - progress
        if remaining_task <= 0.0:
            return ClusterType.NONE

        remaining_time = max(0.0, deadline - elapsed)

        # Slack between deadline and ideal all-OD runtime.
        slack = max(0.0, deadline - task_duration)

        # If we are very close to the deadline in wall-clock terms, force OD.
        # This is an additional safety layer beyond slack-based gating.
        if remaining_time <= remaining_task + dt:
            return ClusterType.ON_DEMAND

        # If there is effectively no slack, always use on-demand to avoid risk.
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        # Wasted time so far: time elapsed minus effective progress.
        wasted = elapsed - progress
        if wasted < 0.0:
            wasted = 0.0

        # Safety margin for allowing further spot usage.
        # Reserve enough slack to absorb:
        # - One more restart overhead.
        # - About two more time steps of worst-case non-progress.
        safety_margin_spot = restart_oh + 2.0 * dt
        if safety_margin_spot < 0.0:
            safety_margin_spot = 0.0

        # If slack is too small to safely use spot with this margin,
        # fall back to always on-demand.
        if slack <= safety_margin_spot:
            if has_spot:
                # Even if spot exists, we can't risk additional overhead.
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND

        # Maximum wasted time at which we still allow spot usage.
        safe_spot_limit_wasted = max(0.0, slack - safety_margin_spot)

        # Hard cutoff: if we've already consumed this much slack,
        # we switch to on-demand exclusively to avoid missing the deadline.
        if wasted >= safe_spot_limit_wasted:
            return ClusterType.ON_DEMAND

        # Decide when to idle (NONE) vs on-demand when spot is unavailable.
        # We allow using some fraction of slack purely for idling early on.
        idle_fraction_of_slack = 0.35  # heuristic, uses at most 35% of slack for idling
        max_idle_wasted = slack * idle_fraction_of_slack

        # We also want to ensure that after idling one more step we still
        # have room to keep using spot safely for a while.
        idle_limit_candidate = min(
            max_idle_wasted,
            safe_spot_limit_wasted - 2.0 * dt,
        )
        if idle_limit_candidate < 0.0:
            idle_limit_candidate = 0.0

        # Now decide the resource for this step.
        if has_spot:
            # Spot is available and we're within safe wasted-time budget.
            return ClusterType.SPOT

        # Spot is unavailable: choose between idling and on-demand.
        # If idling this step would exceed overall slack, we must use OD.
        if wasted + dt > slack:
            return ClusterType.ON_DEMAND

        # If we still have plenty of slack (below idle_limit_candidate),
        # we can afford to idle and wait for cheaper spot instances.
        if wasted <= idle_limit_candidate:
            return ClusterType.NONE

        # Otherwise, consume on-demand to avoid burning too much slack.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)