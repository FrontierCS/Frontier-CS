import math
from typing import List, Dict, Optional, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.restart_counter = 0
        self.spot_unavailable_counter = 0
        self.consecutive_spot = 0
        self.consecutive_od = 0
        self.remaining_work = 0
        self.time_left = 0
        self.critical_zone = False
        self.restart_steps = 0
        self.required_rate = 0
        self.safety_margin = 0
        self.spot_history = []
        self.max_history = 100
        self.spot_availability_rate = 0.5
        self.emergency_mode = False
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def update_state(self, has_spot: bool):
        # Update spot availability history
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > self.max_history:
            self.spot_history.pop(0)
        if len(self.spot_history) > 0:
            self.spot_availability_rate = sum(self.spot_history) / len(self.spot_history)
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        self.remaining_work = self.task_duration - work_done
        
        # Calculate time left
        self.time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate required work rate
        if self.time_left > 0:
            self.required_rate = self.remaining_work / self.time_left
        else:
            self.required_rate = float('inf')
        
        # Calculate safety margin (percentage of time left)
        self.safety_margin = 0.15 * self.time_left  # 15% safety margin
        
        # Calculate restart overhead in steps
        if self.env.gap_seconds > 0:
            self.restart_steps = math.ceil(self.restart_overhead / self.env.gap_seconds)
        
        # Check if we're in critical zone
        self.critical_zone = (self.time_left - self.restart_overhead) < (self.remaining_work * 1.2)
        
        # Emergency mode if we're running out of time
        self.emergency_mode = (self.time_left < self.remaining_work * 1.5) or (self.required_rate > 0.8)
        
        # Update counters
        if has_spot:
            self.spot_unavailable_counter = 0
        else:
            self.spot_unavailable_counter += 1

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state
        self.update_state(has_spot)
        
        # If work is done, stop
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        # If we're in emergency mode, use on-demand
        if self.emergency_mode:
            self.consecutive_od += 1
            self.consecutive_spot = 0
            return ClusterType.ON_DEMAND
        
        # If restart counter is active, wait
        if self.restart_counter > 0:
            self.restart_counter -= 1
            self.consecutive_spot = 0
            self.consecutive_od = 0
            # If critical, don't wait
            if self.critical_zone:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        # If spot is available and we're not in critical zone, use it
        if has_spot and not self.critical_zone:
            # Calculate risk factor based on spot availability history
            risk_factor = 1.0 - self.spot_availability_rate
            
            # If we've had too many consecutive spot instances, be cautious
            if self.consecutive_spot < (3 + int(5 * (1 - risk_factor))):
                # Check if we have enough time buffer
                time_buffer_needed = self.restart_overhead * (1 + risk_factor)
                if self.time_left > self.remaining_work + time_buffer_needed + self.safety_margin:
                    self.consecutive_spot += 1
                    self.consecutive_od = 0
                    return ClusterType.SPOT
        
        # If we're in critical zone or spot not available, use on-demand
        if self.critical_zone or self.spot_unavailable_counter > 2 or self.required_rate > 0.6:
            self.consecutive_od += 1
            self.consecutive_spot = 0
            return ClusterType.ON_DEMAND
        
        # If spot becomes unavailable while we were using it, set restart counter
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.restart_counter = self.restart_steps
        
        # Otherwise, wait (but not if we're falling behind)
        if self.required_rate < 0.4:  # We're ahead of schedule
            self.consecutive_spot = 0
            self.consecutive_od = 0
            return ClusterType.NONE
        else:
            # We're slightly behind but not critical, use on-demand
            self.consecutive_od += 1
            self.consecutive_spot = 0
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
