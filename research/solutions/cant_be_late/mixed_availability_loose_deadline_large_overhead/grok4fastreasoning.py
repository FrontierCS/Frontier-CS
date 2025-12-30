from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - total_done)
        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_work <= 0:
            return ClusterType.NONE
        if remaining_time <= 0:
            return ClusterType.NONE
        slack = remaining_time - remaining_work
        threshold = self.restart_overhead * 20
        if not has_spot or slack <= threshold:
            return ClusterType.ON_DEMAND
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)