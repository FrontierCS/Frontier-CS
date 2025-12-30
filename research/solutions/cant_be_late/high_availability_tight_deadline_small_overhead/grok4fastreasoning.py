from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.guarantee_mode = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - total_done)
        remaining_time = max(0.0, self.deadline - self.env.elapsed_seconds)
        if remaining_work <= 0:
            return ClusterType.NONE
        slack = remaining_time - remaining_work
        if self.guarantee_mode:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        else:
            threshold = 2 * self.restart_overhead
            if slack > threshold:
                return ClusterType.NONE
            else:
                self.guarantee_mode = True
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)