from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_policy"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._od_committed = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done(self) -> float:
        try:
            done_list = getattr(self, "task_done_time", None)
            if done_list is None:
                return 0.0
            s = float(sum(done_list))
            if s < 0:
                return 0.0
            return s
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already decided to stick with On-Demand, never switch away.
        if self._od_committed:
            return ClusterType.ON_DEMAND

        # Progress and remaining work
        done = self._sum_done()
        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining = max(0.0, total - done)

        if remaining <= 1e-9:
            return ClusterType.NONE

        # Time left until deadline
        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = max(0.0, deadline - now)

        # Step size and restart overhead
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # If we are already on OD, overhead to keep using OD is 0. Otherwise, if we commit to OD we pay overhead.
        od_overhead_if_commit_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead

        # If we cannot possibly finish (even with OD), run OD anyway; env will handle penalty.
        if time_left + 1e-9 < remaining:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Decision logic:
        # - If Spot is available:
        #     Use Spot as long as time_left >= remaining + od_overhead_if_commit_now.
        #     Else commit to On-Demand.
        # - If Spot not available:
        #     Wait (NONE) if we still have at least one gap of slack: time_left - (remaining + od_overhead_if_commit_now) >= gap
        #     Else commit to On-Demand.
        if has_spot:
            if time_left + 1e-9 < remaining + od_overhead_if_commit_now:
                self._od_committed = True
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot not available
        slack = time_left - (remaining + od_overhead_if_commit_now)
        if slack + 1e-9 >= gap:
            return ClusterType.NONE

        self._od_committed = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)