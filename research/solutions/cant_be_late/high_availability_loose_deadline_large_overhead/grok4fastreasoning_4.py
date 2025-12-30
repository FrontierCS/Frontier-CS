from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.total_done = 0.0
        self.last_len = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_len = len(self.task_done_time)
        if current_len > self.last_len:
            new_sum = sum(self.task_done_time[self.last_len:])
            self.total_done += new_sum
            self.last_len = current_len
        remaining_work = self.task_duration - self.total_done
        if remaining_work <= 0:
            return ClusterType.NONE
        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_work > remaining_time:
            return ClusterType.ON_DEMAND
        if not has_spot:
            return ClusterType.ON_DEMAND
        buffer_seconds = 2 * 3600
        if remaining_time - remaining_work < buffer_seconds:
            return ClusterType.ON_DEMAND
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)