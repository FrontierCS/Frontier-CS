from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not has_spot:
            return ClusterType.ON_DEMAND

        completed = sum(self.task_done_time)
        remaining = self.task_duration - completed
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        if time_left <= 0:
            return ClusterType.ON_DEMAND

        utilization_needed = remaining / time_left
        threshold = 0.85
        if utilization_needed > threshold:
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)