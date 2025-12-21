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
        remaining = self.task_duration - total_done
        time_left = self.deadline - self.env.elapsed_seconds
        buffer = self.restart_overhead * 10  # 0.5 hours buffer for potential overheads
        if time_left <= remaining + buffer:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
