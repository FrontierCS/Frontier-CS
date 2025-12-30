from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        remaining_time = self.deadline - self.env.elapsed_seconds
        safety = self.restart_overhead * 5  # Approximately 1 hour buffer

        if remaining_work <= 0:
            return ClusterType.NONE

        if not has_spot or remaining_time < remaining_work + safety:
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)