from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.total_completed = 0.0
        self._last_len = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_len = len(self.task_done_time)
        if current_len > self._last_len:
            self.total_completed += sum(self.task_done_time[self._last_len:current_len])
            self._last_len = current_len
        remaining_work = self.task_duration - self.total_completed
        if remaining_work <= 0:
            return ClusterType.NONE
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            return ClusterType.NONE
        slack = time_left - remaining_work
        if has_spot and slack >= self.restart_overhead:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
