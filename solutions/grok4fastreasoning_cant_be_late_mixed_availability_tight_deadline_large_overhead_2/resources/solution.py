from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining = self.task_duration - progress
        gap = self.env.gap_seconds
        time_left = self.deadline - self.env.elapsed_seconds
        remaining_after = max(0.0, remaining - gap)
        time_after = time_left - gap
        if has_spot and (remaining_after == 0 or time_after >= remaining_after + self.restart_overhead):
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
