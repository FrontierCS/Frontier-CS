import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_rate_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        self.last_work_done: float = 0.0
        self.spot_time_chosen: float = 0.0
        self.spot_progress_total: float = 0.0
        
        # Optimistic prior: 10 minutes of trial, 9 minutes of progress
        # Effective rate starts at 0.9
        self.prior_spot_time: float = 600.0
        self.prior_spot_progress: float = 540.0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_work_done = sum(end - start for start, end in self.task_done_time)
        progress_last_step = current_work_done - self.last_work_done

        if last_cluster_type == ClusterType.SPOT:
            self.spot_time_chosen += self.env.gap_seconds
            if progress_last_step > 0:
                self.spot_progress_total += progress_last_step

        work_rem = self.task_duration - current_work_done
        if work_rem <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        numerator = self.spot_progress_total + self.prior_spot_progress
        denominator = self.spot_time_chosen + self.prior_spot_time
        
        effective_spot_rate = numerator / denominator if denominator > 0 else 0

        if time_to_deadline <= 1e-6: # Avoid division by zero or tiny numbers
            required_rate = float('inf')
        else:
            required_rate = work_rem / time_to_deadline

        if has_spot and effective_spot_rate >= required_rate:
            decision = ClusterType.SPOT
        else:
            decision = ClusterType.ON_DEMAND
        
        self.last_work_done = current_work_done

        return decision

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
