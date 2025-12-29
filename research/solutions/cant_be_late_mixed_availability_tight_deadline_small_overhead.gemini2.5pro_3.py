import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.work_done_cache = 0.0
        self.last_task_done_time_len = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if len(self.task_done_time) != self.last_task_done_time_len:
            self.work_done_cache = sum(self.task_done_time)
            self.last_task_done_time_len = len(self.task_done_time)

        work_done = self.work_done_cache
        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_remaining_to_deadline = self.deadline - time_now
        current_slack = time_remaining_to_deadline - work_remaining

        PANIC_THRESHOLD_MULTIPLIER = 10.0
        PANIC_THRESHOLD = PANIC_THRESHOLD_MULTIPLIER * self.restart_overhead

        if current_slack <= PANIC_THRESHOLD:
            return ClusterType.ON_DEMAND

        MIN_BUFFER_H = 1.0
        MAX_BUFFER_H = 3.0
        min_buffer_s = MIN_BUFFER_H * 3600
        max_buffer_s = MAX_BUFFER_H * 3600

        if self.deadline > 1e-9:
            time_fraction = time_now / self.deadline
        else:
            time_fraction = 0

        BUFFER_THRESHOLD = min_buffer_s + (max_buffer_s - min_buffer_s) * time_fraction

        if has_spot:
            return ClusterType.SPOT

        if current_slack <= BUFFER_THRESHOLD:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)