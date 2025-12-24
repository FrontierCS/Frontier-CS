from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.safe_mode = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE
        time_left = self.deadline - self.env.elapsed_seconds
        need_safe = remaining_work > time_left - self.restart_overhead
        if need_safe:
            self.safe_mode = True
        if self.safe_mode or not has_spot:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
