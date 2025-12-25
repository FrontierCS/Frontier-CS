from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining = self.task_duration - progress
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        if remaining <= 0 or time_left <= 0:
            return ClusterType.NONE
        slack = time_left - remaining
        buffer = 2 * self.restart_overhead
        if has_spot and slack > buffer:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)