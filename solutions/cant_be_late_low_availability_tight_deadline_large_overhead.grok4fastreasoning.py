from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_progress = sum(self.task_done_time)
        remaining_work = self.task_duration - total_progress
        if remaining_work <= 0:
            return ClusterType.NONE
        time_left = self.deadline - self.env.elapsed_seconds
        slack_left = time_left - remaining_work
        if slack_left <= 3 * self.restart_overhead:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
