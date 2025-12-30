import math
from typing import List, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args=None):
        super().__init__(args)
        self.spot_price = 0.97  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.restart_hours = 0.20  # hours
        self.initialized = False
        
    def solve(self, spec_path: str) -> "Solution":
        self.initialized = True
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            return ClusterType.NONE
            
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        current_time = self.env.elapsed_seconds / 3600.0  # hours
        remaining_time = self.deadline / 3600.0 - current_time
        
        # If no work left or past deadline, do nothing
        if remaining_work <= 0 or remaining_time <= 0:
            return ClusterType.NONE
        
        # If we're in a restart overhead period, continue with whatever we were doing
        if (last_cluster_type == ClusterType.NONE and 
            self.env.cluster_type != ClusterType.NONE):
            return self.env.cluster_type
        
        # Calculate minimum on-demand time needed to finish
        min_od_time = remaining_work
        
        # Calculate buffer needed for potential spot preemptions
        # Each restart costs restart_hours, but only affects work progress
        # Conservative estimate: assume worst-case preemptions
        safety_buffer = 2.0 * self.restart_hours
        
        # Check if we're in critical zone (need to switch to on-demand)
        critical_zone = remaining_time <= (min_od_time + safety_buffer)
        
        # Decision logic
        if critical_zone:
            # Must use on-demand to guarantee completion
            return ClusterType.ON_DEMAND
        elif has_spot:
            # Use spot if available and we have time buffer
            return ClusterType.SPOT
        elif remaining_time > min_od_time + 2.0 * self.restart_hours:
            # Wait for spot to become available if we have time
            return ClusterType.NONE
        else:
            # Switch to on-demand if waiting would risk missing deadline
            return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)