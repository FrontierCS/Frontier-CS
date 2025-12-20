from typing import Any, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_min_cost"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self._committed_to_od: bool = False
        self._obs_total_steps: int = 0
        self._obs_spot_available_steps: int = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_progress_seconds(self) -> float:
        if not self.task_done_time:
            return 0.0
        try:
            return float(sum(self.task_done_time))
        except Exception:
            total = 0.0
            for v in self.task_done_time:
                try:
                    total += float(v)
                except Exception:
                    continue
            return total

    def _dynamic_margin_seconds(self, gap_seconds: float) -> float:
        # Adaptive safety margin to handle step granularity and trace volatility.
        # 10-30 minutes baseline, scaled by observed spot availability.
        if self._obs_total_steps <= 0:
            avail_ratio = 1.0
        else:
            avail_ratio = self._obs_spot_available_steps / max(1, self._obs_total_steps)

        base_minutes = 10.0 + (1.0 - min(max(avail_ratio, 0.0), 1.0)) * 20.0  # 10 -> 30 minutes
        base_seconds = base_minutes * 60.0
        # Also account for time step granularity: at least 2 steps
        granularity_pad = 2.0 * max(1.0, float(gap_seconds))
        return max(base_seconds, granularity_pad)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update availability observations
        self._obs_total_steps += 1
        if has_spot:
            self._obs_spot_available_steps += 1

        # If already committed to on-demand, never go back to spot.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        gap = float(self.env.gap_seconds)
        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed
        if time_left <= 0:
            # No time left: avoid spending; environment handles completion.
            return ClusterType.NONE

        progress = self._compute_progress_seconds()
        remaining = max(0.0, float(self.task_duration) - progress)
        if remaining <= 0:
            return ClusterType.NONE

        margin = self._dynamic_margin_seconds(gap)

        # Overhead if switching to on-demand now (starting a new instance)
        overhead_switch_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)

        # Commit line: ensure we can always finish on OD (including overhead) before the deadline
        if time_left <= remaining + overhead_switch_now + margin:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available and we still have comfortable slack
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide to wait or commit to OD
        # Safe to wait while there is enough slack to later switch to OD and still finish
        # Overhead to start OD later is restart_overhead
        safe_slack = time_left - (remaining + float(self.restart_overhead))
        if safe_slack > margin:
            return ClusterType.NONE

        # Slack nearly exhausted: commit to OD to guarantee completion
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
