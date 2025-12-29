from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        completed = sum(self.task_done_time)
        remaining = max(0.0, self.task_duration - completed)
        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)
        buffer = 2 * self.restart_overhead  # buffer for possible overheads
        if has_spot and time_left > remaining + buffer:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)