from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.committed_to_od = False
        self.od_commit_time = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        done = 0.0
        try:
            if self.task_done_time:
                done = sum(self.task_done_time)
        except Exception:
            done = 0.0
        rem = self.task_duration - done
        return max(0.0, rem)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining = self._remaining_work()
        if remaining <= 0:
            return ClusterType.NONE

        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        time_left = (self.deadline or 0.0) - elapsed
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        # Safety margin to account for step discretization and action latency
        safety_margin = max(2 * gap, 600.0)  # 10 minutes minimum

        # Decide whether to irrevocably commit to On-Demand to guarantee finishing
        if not self.committed_to_od:
            # Time needed if we switch to OD exactly once from now until finish
            od_time_needed = remaining + (self.restart_overhead or 0.0)
            if time_left <= od_time_needed + safety_margin:
                self.committed_to_od = True
                self.od_commit_time = elapsed

        if self.committed_to_od:
            return ClusterType.ON_DEMAND

        # Not committed: prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and not committed: wait if slack allows
        od_time_needed = remaining + (self.restart_overhead or 0.0)
        slack_extra = time_left - (od_time_needed + safety_margin)

        # Early switch to OD only if we're within a tiny buffer of the commit threshold
        early_switch_buffer = 0.0  # set >0 to start OD slightly before hard commit
        if slack_extra <= early_switch_buffer:
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
