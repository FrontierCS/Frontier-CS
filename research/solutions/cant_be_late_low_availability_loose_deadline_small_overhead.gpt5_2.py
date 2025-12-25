from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_wait_then_od_v2"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._lock_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done(self) -> float:
        if not hasattr(self, "task_done_time") or self.task_done_time is None:
            return 0.0
        return float(sum(self.task_done_time))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already locked to on-demand, always continue on-demand to guarantee finish
        if self._lock_od:
            return ClusterType.ON_DEMAND

        # Gather environment parameters
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        # Compute remaining work and time
        done = self._sum_done()
        remaining_work = max(task_duration - done, 0.0)
        time_remaining = max(deadline - elapsed, 0.0)

        # If nothing left, do nothing
        if remaining_work <= 0.0 or time_remaining <= 0.0:
            return ClusterType.NONE

        # Safety margin to account for discretization
        margin = max(gap, 1e-6)

        # Slack is time_remaining - remaining_work
        slack = time_remaining - remaining_work

        # If slack is at or below the minimal overhead needed to safely switch to OD,
        # lock into OD now to guarantee deadline.
        if slack <= restart_overhead + margin:
            self._lock_od = True
            return ClusterType.ON_DEMAND

        # Not locked: prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: if we can safely wait (even if spot never returns),
        # wait; otherwise, start OD and lock in.
        if slack > restart_overhead + margin:
            return ClusterType.NONE

        self._lock_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)