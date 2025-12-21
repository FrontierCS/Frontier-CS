from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "safety_margin_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        if remaining_work <= 0:
            return ClusterType.NONE
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        if not has_spot:
            return ClusterType.ON_DEMAND
        # has_spot is True
        time_after = max(0, remaining_work - gap)
        extra_overhead = overhead if remaining_work > gap else 0
        worst_case = gap + time_after + extra_overhead
        if remaining_time >= worst_case:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
