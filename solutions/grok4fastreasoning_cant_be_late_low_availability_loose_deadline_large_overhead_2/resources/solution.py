from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        if remaining_work <= 0:
            return ClusterType.NONE
        remaining_wall = self.deadline - self.env.elapsed_seconds
        if remaining_wall <= 0:
            return ClusterType.NONE
        buffer = remaining_wall - remaining_work
        threshold = 2 * self.restart_overhead
        if buffer < threshold:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
