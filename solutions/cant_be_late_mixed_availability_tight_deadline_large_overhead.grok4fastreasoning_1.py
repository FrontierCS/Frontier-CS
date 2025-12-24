from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_done
        if remaining_work <= 0:
            return ClusterType.NONE
        remaining_time = self.deadline - self.env.elapsed_seconds
        slack = remaining_time - remaining_work
        if not has_spot or slack < 2 * self.restart_overhead:
            return ClusterType.ON_DEMAND
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
