from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.total_done = sum(self.task_done_time)
        self.prev_len = len(self.task_done_time)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_len = len(self.task_done_time)
        if current_len > self.prev_len:
            for i in range(self.prev_len, current_len):
                self.total_done += self.task_done_time[i]
            self.prev_len = current_len
        total_done = self.total_done
        if total_done >= self.task_duration:
            return ClusterType.NONE
        remaining_work = self.task_duration - total_done
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            return ClusterType.NONE
        slack = time_left - remaining_work
        threshold = 7200.0  # 2 hours
        use_safe = slack < threshold
        if use_safe:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)