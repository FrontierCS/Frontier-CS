import math
from typing import List
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.initialized = False
        self.conservative_mode = False
        self.spot_availability_history = []
        self.last_decision = None
        self.consecutive_spot_failures = 0
        
    def solve(self, spec_path: str) -> "Solution":
        return self
        
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize on first step
        if not self.initialized:
            self.initialized = True
            self.remaining_work = self.task_duration
            self.spot_available_percentage = 0.6  # initial estimate (between 43-78%)
            self.spot_history_weight = 0.1
        
        # Track spot availability history
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Calculate remaining work and time
        work_done = sum(segment.length for segment in self.task_done_time)
        self.remaining_work = self.task_duration - work_done
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Update spot availability estimate based on history
        if len(self.spot_availability_history) > 0:
            recent_availability = sum(self.spot_availability_history[-20:]) / min(20, len(self.spot_availability_history))
            self.spot_available_percentage = (0.7 * self.spot_available_percentage + 
                                            0.3 * recent_availability)
        
        # Check if we should be conservative (safety first)
        self.conservative_mode = self._should_be_conservative(time_left)
        
        # Decide next action
        decision = self._make_decision(last_cluster_type, has_spot, time_left)
        self.last_decision = decision
        
        # Update spot failure tracking
        if has_spot and decision == ClusterType.SPOT:
            self.consecutive_spot_failures = 0
        elif not has_spot and decision == ClusterType.SPOT:
            self.consecutive_spot_failures += 1
        
        return decision
    
    def _should_be_conservative(self, time_left: float) -> bool:
        """Determine if we need to be conservative to meet deadline"""
        # Calculate expected completion time with current strategy
        if self.remaining_work <= 0:
            return False
            
        # Conservative factors
        safety_factor = 1.2  # 20% safety margin
        min_safety_time = 2 * self.restart_overhead  # at least 2 restarts worth of safety
        
        # Calculate effective work rate
        effective_spot_rate = self.spot_available_percentage
        spot_time_needed = self.remaining_work / effective_spot_rate
        
        # If we're getting close to deadline, be conservative
        if time_left < spot_time_needed * safety_factor + min_safety_time:
            return True
            
        # If we've had recent spot failures
        if self.consecutive_spot_failures > 3:
            return True
            
        return False
    
    def _make_decision(self, last_cluster_type: ClusterType, has_spot: bool, time_left: float) -> ClusterType:
        """Make the decision based on current state"""
        
        # If no work left, do nothing
        if self.remaining_work <= 0:
            return ClusterType.NONE
            
        # In conservative mode, prefer on-demand
        if self.conservative_mode:
            if self.remaining_work <= time_left:
                # We have enough time even with conservative approach
                if has_spot and self._should_use_spot_conservative(time_left):
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # We're behind schedule - must use on-demand
                return ClusterType.ON_DEMAND
        
        # Regular decision making
        if has_spot:
            # Use spot if we have enough time buffer
            time_needed_with_spot = self.remaining_work / self.spot_available_percentage
            time_needed_with_ondemand = self.remaining_work
            
            # Consider restart overhead
            if last_cluster_type != ClusterType.SPOT and last_cluster_type != ClusterType.NONE:
                time_needed_with_spot += self.restart_overhead
            
            # Decision: use spot if we have enough buffer
            buffer_needed = 2 * self.restart_overhead
            if time_left > time_needed_with_spot + buffer_needed:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            # Spot not available
            if time_left > self.remaining_work + self.restart_overhead:
                # We can afford to wait for spot
                return ClusterType.NONE
            else:
                # Need to use on-demand to meet deadline
                return ClusterType.ON_DEMAND
    
    def _should_use_spot_conservative(self, time_left: float) -> bool:
        """Decide whether to use spot in conservative mode"""
        # Only use spot if we have significant time buffer
        min_buffer = 4 * self.restart_overhead
        expected_spot_time = self.remaining_work / max(self.spot_available_percentage, 0.5)
        
        return time_left > expected_spot_time + min_buffer
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
