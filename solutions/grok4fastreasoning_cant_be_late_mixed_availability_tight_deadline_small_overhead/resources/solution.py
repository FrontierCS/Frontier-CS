from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining = self.task_duration - progress
        if remaining <= 0:
            return ClusterType.NONE
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        if progress == 0:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        overhead = elapsed - progress
        rate = overhead / progress
        projected_additional = rate * remaining
        projected_t = elapsed + remaining + projected_additional
        if projected_t > self.deadline or time_left < remaining + self.restart_overhead:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
