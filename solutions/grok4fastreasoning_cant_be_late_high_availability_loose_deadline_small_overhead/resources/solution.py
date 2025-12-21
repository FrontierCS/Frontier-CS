from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        if total_done >= self.task_duration:
            return ClusterType.NONE
        if has_spot:
            return ClusterType.SPOT
        remaining_work = self.task_duration - total_done
        time_left = self.deadline - self.env.elapsed_seconds
        if remaining_work > time_left:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
