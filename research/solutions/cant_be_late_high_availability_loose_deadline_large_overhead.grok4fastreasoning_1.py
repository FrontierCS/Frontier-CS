from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining = self.task_duration - progress
        time_left = self.deadline - self.env.elapsed_seconds
        if remaining <= 0:
            return ClusterType.NONE
        buffer = 2 * self.restart_overhead
        if time_left < remaining + buffer or not has_spot:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)