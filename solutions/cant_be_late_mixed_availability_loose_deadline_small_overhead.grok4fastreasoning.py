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
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            return ClusterType.NONE
        slack = time_left - remaining_work
        threshold = 2 * self.restart_overhead
        if slack < threshold:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
