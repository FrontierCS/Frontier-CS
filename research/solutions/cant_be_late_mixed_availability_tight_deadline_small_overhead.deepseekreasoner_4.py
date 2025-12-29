import heapq
import math
from typing import List, Dict, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__()
        self.spot_price = 0.97  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.price_ratio = self.spot_price / self.ondemand_price
        self.safety_multiplier = 2.5
        self.min_safety_time = 3600  # 1 hour minimum
        self.max_safety_time = 14400  # 4 hours maximum
        self.spot_available_history = []
        self.spot_unavailable_streak = 0
        self.max_unacceptable_streak = 10
        self.work_done = 0.0
        self.consecutive_none_steps = 0
        self.max_none_steps = 15
        
    def solve(self, spec_path: str) -> "Solution":
        # Could read config from spec_path if needed
        return self
    
    def _compute_safety_margin(self, work_remaining: float) -> float:
        base_margin = self.restart_overhead * self.safety_multiplier
        dynamic_margin = work_remaining * 0.15  # 15% of remaining work
        safety = max(base_margin, dynamic_margin)
        safety = min(safety, self.max_safety_time)
        safety = max(safety, self.min_safety_time)
        return safety
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update history
        self.spot_available_history.append(1 if has_spot else 0)
        if len(self.spot_available_history) > 50:
            self.spot_available_history.pop(0)
        
        # Update streak counter
        if not has_spot:
            self.spot_unavailable_streak += 1
        else:
            self.spot_unavailable_streak = 0
        
        # Calculate work completed so far
        work_completed = sum(self.task_done_time) if self.task_done_time else 0.0
        self.work_done = work_completed
        
        # Remaining work and time
        work_remaining = max(0.0, self.task_duration - work_completed)
        time_remaining = max(0.0, self.deadline - self.env.elapsed_seconds)
        
        # If work is done, use NONE
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # If we're out of time, must use on-demand
        if time_remaining <= 0:
            return ClusterType.ON_DEMAND
        
        # Calculate time needed at different rates
        time_needed_on_demand = work_remaining
        safety_margin = self._compute_safety_margin(work_remaining)
        time_needed_with_buffer = time_needed_on_demand + safety_margin
        
        # Check if we must switch to on-demand to meet deadline
        if time_remaining <= time_needed_with_buffer:
            return ClusterType.ON_DEMAND
        
        # Calculate spot availability metrics
        spot_availability = (sum(self.spot_available_history) / len(self.spot_available_history) 
                            if self.spot_available_history else 0.0)
        
        # If spot is consistently unavailable, consider switching
        if (self.spot_unavailable_streak > self.max_unacceptable_streak and 
            time_needed_on_demand < time_remaining * 0.9):
            return ClusterType.ON_DEMAND
        
        # Decide based on availability and risk
        if has_spot:
            # Calculate expected time with spot including overhead
            expected_efficiency = max(0.5, spot_availability * 0.9)
            expected_spot_time = work_remaining / expected_efficiency
            
            # If we can comfortably finish with spot
            if (expected_spot_time * 1.2 < time_remaining and 
                spot_availability > 0.4):
                return ClusterType.SPOT
            
            # If moderately risky but worth it
            if (expected_spot_time * 1.5 < time_remaining and 
                spot_availability > 0.3 and 
                self.consecutive_none_steps < self.max_none_steps):
                return ClusterType.SPOT
            
            # If we have plenty of time, use spot
            if time_remaining > work_remaining * 3:
                return ClusterType.SPOT
            
            # Otherwise be conservative
            return ClusterType.ON_DEMAND
        else:
            # Spot not available
            self.consecutive_none_steps += 1
            
            # If we can afford to wait
            if (time_remaining > time_needed_on_demand * 1.5 and 
                self.consecutive_none_steps < self.max_none_steps):
                return ClusterType.NONE
            else:
                self.consecutive_none_steps = 0
                return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)