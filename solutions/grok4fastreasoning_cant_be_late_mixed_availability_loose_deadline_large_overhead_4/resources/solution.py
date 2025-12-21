from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        remaining = self.task_duration - done
        if remaining <= 0:
            return ClusterType.NONE
        t_left = self.deadline - self.env.elapsed_seconds
        if t_left <= 0:
            return ClusterType.NONE
        use_spot = has_spot and (t_left >= remaining + self.restart_overhead)
        if use_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
