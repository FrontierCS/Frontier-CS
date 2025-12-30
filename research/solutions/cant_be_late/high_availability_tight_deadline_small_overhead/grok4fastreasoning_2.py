from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        safe_for_spot = time_left >= remaining_work + self.restart_overhead
        if last_cluster_type == ClusterType.SPOT and has_spot:
            return ClusterType.SPOT
        elif last_cluster_type == ClusterType.ON_DEMAND:
            if has_spot and safe_for_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            if has_spot and safe_for_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)