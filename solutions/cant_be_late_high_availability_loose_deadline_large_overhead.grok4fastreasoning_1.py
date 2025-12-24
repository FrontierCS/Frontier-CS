from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        time_left = self.deadline - self.env.elapsed_seconds

        if remaining_work <= 0:
            return ClusterType.NONE

        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            # Switching to SPOT, check safety
            if remaining_work <= time_left - self.restart_overhead:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
