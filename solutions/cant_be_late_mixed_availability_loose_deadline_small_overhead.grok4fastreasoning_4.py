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
        rem_work = self.task_duration - done
        rem_time = self.deadline - self.env.elapsed_seconds
        slack = rem_time - rem_work
        threshold = 4 * 3600  # 4 hours in seconds
        if slack < threshold:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
