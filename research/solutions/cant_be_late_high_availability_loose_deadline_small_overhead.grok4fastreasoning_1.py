from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "safe_spot"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        if done >= self.task_duration:
            return ClusterType.NONE
        elapsed = self.env.elapsed_seconds
        if elapsed >= self.deadline:
            return ClusterType.NONE
        remaining = self.task_duration - done
        time_left = self.deadline - elapsed
        buffer = self.restart_overhead * 5
        if time_left < remaining + buffer:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)