from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "util_threshold"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - total_done)
        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed
        if time_left <= 0 or remaining_work <= 0:
            return ClusterType.NONE
        utilization = remaining_work / time_left if time_left > 0 else float('inf')
        threshold = 0.95
        if has_spot and utilization < threshold:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
