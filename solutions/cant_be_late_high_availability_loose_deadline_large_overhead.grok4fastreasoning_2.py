from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        if self.task_duration <= done:
            return ClusterType.NONE
        remaining = self.task_duration - done
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        if time_left <= 0:
            return ClusterType.NONE
        safety_margin = self.restart_overhead * 5
        if time_left < remaining + safety_margin:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
