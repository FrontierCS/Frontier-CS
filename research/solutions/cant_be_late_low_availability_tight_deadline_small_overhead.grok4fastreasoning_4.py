from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.total_done = 0.0
        self.prev_len = len(self.task_done_time)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_len = len(self.task_done_time)
        if current_len > self.prev_len:
            added = sum(self.task_done_time[self.prev_len:current_len])
            self.total_done += added
            self.prev_len = current_len
        total_done = self.total_done
        remaining = self.task_duration - total_done
        if remaining <= 0:
            return ClusterType.NONE
        time_left = self.deadline - self.env.elapsed_seconds
        if has_spot and time_left >= remaining + self.restart_overhead:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)