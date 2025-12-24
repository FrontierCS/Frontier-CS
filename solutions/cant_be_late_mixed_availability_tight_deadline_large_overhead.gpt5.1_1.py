from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._force_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could parse spec_path; not needed for this heuristic.
        return self

    def _estimate_task_done(self) -> float:
        """Best-effort estimation of completed task duration in seconds."""
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0

        task_dur = getattr(self, "task_duration", None)
        try:
            td = float(task_dur) if task_dur is not None else None
        except Exception:
            td = None

        first = tdt[0]

        # Case 1: list of (start, end) segments
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            total = 0.0
            for seg in tdt:
                try:
                    if not (isinstance(seg, (list, tuple)) and len(seg) >= 2):
                        continue
                    start = float(seg[0])
                    end = float(seg[1])
                    if end > start:
                        total += end - start
                except Exception:
                    continue
            if td is not None:
                total = min(total, td)
            return max(0.0, total)

        # Case 2: list of numeric values: either cumulative or segment durations
        try:
            values = [float(x) for x in tdt]
        except Exception:
            return 0.0

        if not values:
            return 0.0

        maxv = max(values)
        is_non_decreasing = all(
            values[i] <= values[i + 1] + 1e-6 for i in range(len(values) - 1)
        )

        # Heuristic:
        # - If values are non-decreasing and bounded by task_duration, treat as cumulative
        # - Otherwise, treat as segment durations and sum them
        if td is not None and maxv <= td + 1e-6 and is_non_decreasing:
            done = values[-1]
        else:
            done = sum(v for v in values if v > 0.0)
            if td is not None:
                done = min(done, td)

        return max(0.0, done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already decided to stick with on-demand, keep doing so.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Ensure required attributes exist; if not, default safe behavior (on-demand).
        if not hasattr(self, "env") or self.env is None:
            return ClusterType.ON_DEMAND
        if not hasattr(self.env, "elapsed_seconds") or not hasattr(
            self.env, "gap_seconds"
        ):
            return ClusterType.ON_DEMAND
        if not hasattr(self, "task_duration") or not hasattr(self, "deadline"):
            return ClusterType.ON_DEMAND
        if not hasattr(self, "restart_overhead"):
            return ClusterType.ON_DEMAND

        elapsed = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        restart_overhead = float(self.restart_overhead)
        task_duration = float(self.task_duration)

        # Compute progress and remaining work.
        done = self._estimate_task_done()
        done = max(0.0, min(done, task_duration))
        remaining = max(0.0, task_duration - done)

        time_left = max(0.0, deadline - elapsed)

        # Time needed if we switch to on-demand and never leave it:
        # restart_overhead (single restart) + remaining work.
        required_od_time = remaining + restart_overhead

        # Safety buffer to account for discretization and modeling mismatches.
        # Units are seconds.
        time_buffer = max(2.0 * gap, 0.5 * restart_overhead)

        # If even with immediate switch to on-demand we are too tight, force on-demand now.
        if time_left <= required_od_time + time_buffer:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # We are in the "safe zone": can still afford to rely on spot instances.

        if has_spot:
            # Prefer spot when available and we're safely ahead of the deadline.
            return ClusterType.SPOT

        # Spot not available this step.
        # Decide between idling and starting on-demand early.
        # Check if idling for one more step is still safe.
        projected_time_left = max(0.0, time_left - gap)
        if projected_time_left > required_od_time + time_buffer:
            # Still safe to wait for spot; do nothing this step.
            return ClusterType.NONE

        # We can't afford to wait; start on-demand now.
        self._force_on_demand = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
