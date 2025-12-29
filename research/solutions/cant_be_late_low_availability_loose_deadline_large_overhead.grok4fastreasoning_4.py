from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "conservative_spot"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        completed = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - completed)
        elapsed = self.env.elapsed_seconds
        time_left = max(0.0, self.deadline - elapsed)
        if remaining_work == 0:
            return ClusterType.NONE
        slack = time_left - remaining_work
        if slack < self.restart_overhead or not has_spot:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)