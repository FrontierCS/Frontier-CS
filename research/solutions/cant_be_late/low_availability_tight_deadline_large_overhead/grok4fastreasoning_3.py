from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        remaining_wall = self.deadline - self.env.elapsed_seconds
        if remaining_work <= 0:
            return ClusterType.NONE
        if not has_spot:
            return ClusterType.ON_DEMAND
        if remaining_wall >= remaining_work + self.restart_overhead:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)