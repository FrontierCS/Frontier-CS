import math
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_history = []
        self.spot_availability_rate = 0.5
        self.remaining_work = 0
        self.time_left = 0
        self.safe_time_margin = 0
        self.critical_time_margin = 0
        self.conservative_threshold = 0
        self.overhead_remaining = 0
        self.last_action = ClusterType.NONE
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _update_state(self, last_cluster_type: ClusterType, has_spot: bool):
        # Update spot availability history
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
        
        # Calculate current spot availability rate
        if self.spot_history:
            self.spot_availability_rate = sum(self.spot_history) / len(self.spot_history)
        
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        self.remaining_work = self.task_duration - work_done
        self.time_left = self.deadline - self.env.elapsed_seconds
        
        # Update restart overhead tracking
        if last_cluster_type == ClusterType.SPOT:
            self.overhead_remaining = 0
        elif self.overhead_remaining > 0:
            self.overhead_remaining = max(0, self.overhead_remaining - self.env.gap_seconds)
        
        # Adjust thresholds based on situation
        if self.time_left > 0:
            required_rate = self.remaining_work / self.time_left
            self.safe_time_margin = min(2.0 * self.restart_overhead, self.time_left * 0.1)
            self.critical_time_margin = min(4.0 * self.restart_overhead, self.time_left * 0.2)
            
            # Conservative threshold: if we need high completion rate, be more conservative
            if required_rate > 0.95:
                self.conservative_threshold = 0.7
            elif required_rate > 0.9:
                self.conservative_threshold = 0.6
            elif required_rate > 0.8:
                self.conservative_threshold = 0.5
            else:
                self.conservative_threshold = 0.4
    
    def _should_use_spot(self, has_spot: bool) -> bool:
        if not has_spot:
            return False
        
        # If time is critical, be more conservative
        time_ratio = self.time_left / self.task_duration if self.task_duration > 0 else 1.0
        if time_ratio < 0.15:
            return self.spot_availability_rate > 0.8
        
        # Adjust threshold based on remaining work
        if self.remaining_work > 12 * 3600:  # More than 12 hours left
            return self.spot_availability_rate > self.conservative_threshold
        elif self.remaining_work > 6 * 3600:  # 6-12 hours left
            return self.spot_availability_rate > self.conservative_threshold + 0.1
        else:  # Less than 6 hours left
            return self.spot_availability_rate > self.conservative_threshold + 0.2
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_state(last_cluster_type, has_spot)
        
        # If no work left, do nothing
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        # Emergency mode: if we're running out of time
        emergency_threshold = self.restart_overhead * 2
        if self.time_left < emergency_threshold and self.remaining_work > 0:
            return ClusterType.ON_DEMAND
        
        # If we're in a restart overhead period and spot is available, continue with spot
        if self.overhead_remaining > 0 and has_spot:
            return ClusterType.SPOT
        
        # Calculate efficient decision
        if self._should_use_spot(has_spot):
            # Check if we have enough time to absorb potential preemption
            if self.time_left - self.safe_time_margin > self.restart_overhead:
                self.last_action = ClusterType.SPOT
                return ClusterType.SPOT
        
        # If we need to catch up on work
        required_rate = self.remaining_work / self.time_left if self.time_left > 0 else float('inf')
        if required_rate > 0.9:  # Falling behind
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # If spot is unreliable for current needs
        if not has_spot or self.spot_availability_rate < 0.3:
            if self.remaining_work / (self.time_left - self.critical_time_margin) > 0.8:
                self.last_action = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
        
        # Default to on-demand if we're unsure
        if self.time_left < self.critical_time_margin:
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Use spot if available and we have time buffer
        if has_spot and self.time_left > self.safe_time_margin:
            self.last_action = ClusterType.SPOT
            return ClusterType.SPOT
        
        # Otherwise use on-demand
        self.last_action = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)