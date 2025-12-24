from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if has_spot:
            return ClusterType.SPOT

        completed = sum(self.task_done_time)
        remaining_work = self.task_duration - completed
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            return ClusterType.NONE

        extra_overhead = self.restart_overhead if last_cluster_type == ClusterType.SPOT else 0
        required_time = remaining_work + extra_overhead
        required_rate = required_time / time_left

        threshold = 0.5
        if required_rate > threshold:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
