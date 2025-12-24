from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        completed = sum(self.task_done_time)
        remaining_work = self.task_duration - completed
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            return ClusterType.NONE
        if time_left <= remaining_work:
            return ClusterType.ON_DEMAND
        slack = time_left - remaining_work
        safety = 7200  # 2 hours in seconds
        if slack < safety:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
