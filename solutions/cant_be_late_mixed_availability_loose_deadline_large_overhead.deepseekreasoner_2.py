import sys
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.remaining_work = 0.0
        self.restart_timer = 0.0
        self.wait_start = None
        self.max_wait = 3600.0
        self.threshold_multiplier = 4.0
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate total work done
        total_done = sum(end - start for start, end in self.task_done_time)
        self.remaining_work = self.task_duration - total_done
        
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        
        # Update restart timer
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.restart_timer = self.restart_overhead
        else:
            if self.restart_timer > 0:
                self.restart_timer -= self.env.gap_seconds
                if self.restart_timer < 0:
                    self.restart_timer = 0.0
        
        # Handle restart overhead period
        if self.restart_timer > 0:
            time_needed = self.restart_timer + self.remaining_work
            if time_needed <= time_left:
                return ClusterType.NONE
            else:
                self.restart_timer = self.restart_overhead
                return ClusterType.ON_DEMAND
        
        # Not in restart overhead
        threshold = self.threshold_multiplier * self.restart_overhead
        time_needed_od = current_time + self.remaining_work
        
        if time_needed_od >= self.deadline - threshold:
            self.wait_start = None
            return ClusterType.ON_DEMAND
        
        if has_spot:
            self.wait_start = None
            return ClusterType.SPOT
        
        # Spot unavailable - decide whether to wait
        if self.wait_start is None:
            self.wait_start = current_time
        
        if current_time - self.wait_start > self.max_wait:
            self.wait_start = None
            return ClusterType.ON_DEMAND
        
        return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
