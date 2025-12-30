import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.spot_history = []
        self.spot_price = 0.97
        self.od_price = 3.06
        self.safety_buffer = None
        self.conservative_threshold = None
        self.emergency_threshold = None
        self.initialized = False

    def solve(self, spec_path: str) -> "Solution":
        # Read configuration if spec_path is provided
        # For this implementation, we'll use hardcoded values based on problem description
        self.safety_buffer = 3600 * 2  # 2 hours safety buffer
        self.conservative_threshold = 0.15  # Switch to OD when spot availability drops below 15%
        self.emergency_threshold = 0.10  # Emergency threshold for immediate switch
        self.initialized = True
        return self

    def _calculate_spot_availability_rate(self, window=100):
        """Calculate recent spot availability rate"""
        if not self.spot_history:
            return 0.0
        recent = self.spot_history[-min(window, len(self.spot_history)):]
        return sum(recent) / len(recent)

    def _should_switch_to_od(self, last_cluster_type, has_spot, remaining_work, remaining_time):
        """Decision logic for switching to on-demand"""
        # If spot is not available, we must consider OD
        if not has_spot:
            return True
            
        # If we're in emergency mode (very close to deadline), use OD
        if remaining_time - remaining_work < self.safety_buffer:
            return True
            
        # Calculate spot availability history
        spot_availability = self._calculate_spot_availability_rate()
        
        # If spot availability is very low, switch to OD
        if spot_availability < self.emergency_threshold:
            return True
            
        # If we just had a preemption and spot availability is low
        if (last_cluster_type == ClusterType.SPOT and not has_spot and 
            spot_availability < self.conservative_threshold):
            return True
            
        # If remaining time is tight considering restart overhead
        time_needed_with_overhead = remaining_work + self.restart_overhead
        if remaining_time < time_needed_with_overhead * 1.5:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Track spot availability history
        self.spot_history.append(1 if has_spot else 0)
        
        # Calculate remaining work and time
        completed_work = sum(self.task_done_time)
        remaining_work = max(0, self.task_duration - completed_work)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # If no work remains, return NONE to save cost
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If remaining time is insufficient even with OD, still try
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND
            
        # Emergency: must finish very soon
        time_remaining_ratio = remaining_time / max(remaining_work, 0.1)
        if time_remaining_ratio < 1.2:  # Less than 20% slack
            return ClusterType.ON_DEMAND
        
        # Decision logic
        if self._should_switch_to_od(last_cluster_type, has_spot, remaining_work, remaining_time):
            return ClusterType.ON_DEMAND
        elif has_spot:
            # Use spot if available and conditions are favorable
            return ClusterType.SPOT
        else:
            # If spot not available but not critical, wait
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)