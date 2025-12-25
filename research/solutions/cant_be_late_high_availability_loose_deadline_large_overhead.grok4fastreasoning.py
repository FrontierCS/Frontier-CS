from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        if self.task_duration <= done:
            return ClusterType.NONE
        remaining = self.task_duration - done
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        slack = time_left - remaining
        safety = 3 * self.restart_overhead
        if not has_spot or slack < safety:
            return ClusterType.ON_DEMAND
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)