from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        remaining = self.task_duration - total_done
        time_left = self.deadline - self.env.elapsed_seconds
        if remaining <= 0 or time_left <= 0:
            return ClusterType.NONE
        if not has_spot:
            return ClusterType.ON_DEMAND
        slack_ratio = time_left / remaining if remaining > 0 else float('inf')
        if slack_ratio > 1.1:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
