from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self._lock_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task completed, do nothing.
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining = max(0.0, self.task_duration - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        # If already committed to On-Demand, keep using it to guarantee completion.
        if self._lock_to_od:
            return ClusterType.ON_DEMAND

        # Compute slack and safety margins.
        t = self.env.elapsed_seconds
        slack = self.deadline - t
        gap = self.env.gap_seconds
        # Safety margin accounts for one decision interval and a small fraction of restart overhead.
        safety_margin = max(gap, 1.0) + 0.1 * self.restart_overhead

        # Determine if we must commit to On-Demand now to guarantee finishing before the deadline.
        # Conservatively include a restart overhead when switching to OD.
        need_od = slack <= (remaining + self.restart_overhead + safety_margin)

        if need_od:
            self._lock_to_od = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available; otherwise wait (NONE) to avoid unnecessary OD cost/overhead.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
