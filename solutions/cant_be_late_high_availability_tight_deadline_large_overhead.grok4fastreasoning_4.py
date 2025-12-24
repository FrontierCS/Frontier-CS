from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        completed = sum(self.task_done_time)
        remaining_work = self.task_duration - completed
        if remaining_work <= 0:
            return ClusterType.NONE
        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_time <= 0:
            return ClusterType.NONE
        slack = remaining_time - remaining_work
        use_od = (slack <= self.restart_overhead * 2) or (remaining_work / remaining_time >= 0.95)
        if use_od:
            return ClusterType.ON_DEMAND
        elif has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
