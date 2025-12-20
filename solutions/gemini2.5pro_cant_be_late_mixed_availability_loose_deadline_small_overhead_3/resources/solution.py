import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.buffer_start_h = 1.5
        self.buffer_end_h = 4.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.task_done_time:
            total_work_done = 0.0
        else:
            total_work_done = sum(end - start for start, end in self.task_done_time)

        work_remaining = self.task_duration - total_work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        if work_remaining >= time_to_deadline:
            return ClusterType.ON_DEMAND
             
        current_slack = time_to_deadline - work_remaining

        if self.task_duration > 0:
            progress_fraction = total_work_done / self.task_duration
        else:
            progress_fraction = 1.0

        current_buffer_h = self.buffer_start_h * (1 - progress_fraction) + self.buffer_end_h * progress_fraction
        safety_buffer_seconds = current_buffer_h * 3600.0

        if has_spot:
            return ClusterType.SPOT

        if current_slack <= safety_buffer_seconds:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
