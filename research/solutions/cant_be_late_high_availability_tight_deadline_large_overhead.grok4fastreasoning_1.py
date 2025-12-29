from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not has_spot:
            return ClusterType.ON_DEMAND
        total_done = sum(self.task_done_time)
        remaining = max(0.0, self.task_duration - total_done)
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= remaining + self.restart_overhead:
            return ClusterType.ON_DEMAND
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)