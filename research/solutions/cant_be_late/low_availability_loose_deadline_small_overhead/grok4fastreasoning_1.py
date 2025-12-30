from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if has_spot:
            return ClusterType.SPOT

        done = sum(self.task_done_time)
        remaining = self.task_duration - done
        if remaining <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        time_left = self.deadline - time_now

        skip_time_left = time_left - gap
        buffer_factor = 1.05
        can_skip = skip_time_left >= remaining * buffer_factor

        if can_skip:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)