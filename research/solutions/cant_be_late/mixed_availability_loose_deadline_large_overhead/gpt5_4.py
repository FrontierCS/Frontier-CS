from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_commit_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self._commit_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        done = 0.0
        try:
            if self.task_done_time:
                done = float(sum(self.task_done_time))
        except Exception:
            done = 0.0
        remain = float(self.task_duration) - done
        if remain < 0.0:
            remain = 0.0
        return remain

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Compute basic quantities
        remain = self._remaining_work()
        if remain <= 0.0:
            return ClusterType.NONE

        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        if time_left <= 0.0:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        gap = float(self.env.gap_seconds)
        restart = float(self.restart_overhead)

        # Safety margin to account for restart overhead and discretization
        T_margin = 2.0 * restart + 3.0 * gap

        # If already committed to OD, stay on OD
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Commit to OD if we're approaching the critical boundary
        if time_left <= (remain + T_margin):
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available and we have ample slack
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: wait if we can afford at least one more gap safely, else commit to OD
        if (time_left - gap) > (remain + T_margin):
            return ClusterType.NONE

        self._commit_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)