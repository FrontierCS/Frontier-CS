from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.FINISH_MOVE_MULTIPLIER = 5.0
        self.CRITICAL_BUFFER_C_MIN = 1.5
        self.CRITICAL_BUFFER_C_MAX_ADD = 8.5
        self.WAIT_PATIENCE_SECONDS = 3600.0

        self.finish_move_threshold = self.FINISH_MOVE_MULTIPLIER * self.restart_overhead
        return self

    def _get_work_done(self) -> float:
        return sum(end - start for start, end in self.task_done_time)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        work_done = self._get_work_done()

        if work_done >= self.task_duration:
            return ClusterType.NONE

        work_left = self.task_duration - work_done
        time_now = self.env.elapsed_seconds
        time_left = self.deadline - time_now

        if time_left < work_left:
            return ClusterType.ON_DEMAND
        
        current_slack = time_left - work_left

        if work_left <= self.finish_move_threshold:
            return ClusterType.ON_DEMAND

        progress = work_done / self.task_duration if self.task_duration > 0 else 1.0

        c_factor = self.CRITICAL_BUFFER_C_MIN + self.CRITICAL_BUFFER_C_MAX_ADD * (progress**2)
        critical_buffer = c_factor * self.restart_overhead
        
        if current_slack <= critical_buffer:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        wait_buffer = critical_buffer + self.WAIT_PATIENCE_SECONDS
        
        if current_slack <= wait_buffer:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)