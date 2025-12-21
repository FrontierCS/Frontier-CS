import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.use_spot_until = 0
        self.critical_threshold = 0
        self.initialized = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_if_needed(self, work_left, time_left):
        if not self.initialized:
            self.initialized = True
            total_hours = self.task_duration / 3600
            deadline_hours = self.deadline / 3600
            slack = deadline_hours - total_hours
            
            base_buffer = self.restart_overhead * 3
            self.critical_threshold = max(
                work_left + base_buffer,
                work_left * 1.1
            )
            
            self.use_spot_until = time_left - self.critical_threshold

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        time_left = self.deadline - elapsed
        
        if work_left <= 0:
            return ClusterType.NONE
            
        self._initialize_if_needed(work_left, time_left)
        
        cannot_finish_on_spot = time_left < work_left + self.restart_overhead
        
        if cannot_finish_on_spot:
            return ClusterType.ON_DEMAND
        
        if not has_spot:
            return ClusterType.NONE
        
        time_needed_if_od = work_left
        time_needed_if_spot = work_left + self.restart_overhead
        
        progress_rate = work_done / elapsed if elapsed > 0 else 1.0
        expected_spot_time = work_left / progress_rate if progress_rate > 0 else work_left
        
        buffer_needed = self.restart_overhead * (1 + (52 * 3600 - elapsed) / (4 * 3600))
        
        if time_left < expected_spot_time + buffer_needed:
            return ClusterType.ON_DEMAND
        
        if time_left > self.use_spot_until:
            return ClusterType.SPOT
        
        remaining_slack = time_left - work_left
        spot_risk_tolerance = self.restart_overhead * 4
        
        if remaining_slack < spot_risk_tolerance:
            return ClusterType.ON_DEMAND
        
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
