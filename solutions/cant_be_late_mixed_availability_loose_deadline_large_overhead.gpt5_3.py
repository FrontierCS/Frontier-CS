from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._commit_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _pad_seconds(self, gap: float) -> float:
        # Conservative padding to account for discretization and minor uncertainties.
        # Use small, time-step-aware buffer. Do not exceed 15 minutes.
        base = max(2.0 * gap, 0.1 * float(self.restart_overhead))
        return min(base + 60.0, 900.0)

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        return max(0.0, float(self.task_duration) - float(done))

    def _safe_to_wait_one_step(self, rem_time: float, rem_work: float, gap: float, overhead_needed: float, pad: float) -> bool:
        return (rem_time - gap) >= (rem_work + overhead_needed + pad)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep using it to guarantee completion.
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        now = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        rem_time = max(0.0, float(self.deadline) - now)
        rem_work = self._remaining_work()
        pad = self._pad_seconds(gap)

        # Overhead needed if we were to start (or switch to) on-demand from current state.
        overhead_needed = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)

        # Commit to on-demand if we're within the fallback window.
        if rem_time <= (rem_work + overhead_needed + pad):
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Not yet committed to OD:
        if has_spot:
            return ClusterType.SPOT

        # Spot not available; decide to wait (NONE) or run OD for this step.
        if self._safe_to_wait_one_step(rem_time, rem_work, gap, overhead_needed, pad):
            return ClusterType.NONE

        # Can't safely wait; use on-demand for this step (but do not necessarily commit).
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
