import argparse
import math
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self._initialize_state()
    
    def _initialize_state(self):
        """Initialize tracking variables"""
        self.spot_price = None
        self.on_demand_price = None
        self.step_size = None
        self.steps_per_hour = None
        self.overhead_steps = None
        self.work_remaining = None
        self.deadline_steps = None
        self.current_step = 0
        self.overhead_remaining = 0
        self.spot_unavailable_count = 0
        self.consecutive_spot_work = 0
        self.spot_usage_history = []
        self.on_demand_used = 0
        self.risk_factor = 1.0
    
    def solve(self, spec_path: str) -> "Solution":
        """Optional initialization - read spec if needed"""
        return self
    
    def _update_state(self, last_cluster_type: ClusterType, has_spot: bool):
        """Update internal state tracking"""
        self.current_step += 1
        
        # First call initialization
        if self.step_size is None:
            self.step_size = self.env.gap_seconds
            self.steps_per_hour = 3600 / self.step_size
            self.overhead_steps = math.ceil(self.restart_overhead / self.step_size)
            self.deadline_steps = self.deadline / self.step_size
            
        if self.work_remaining is None:
            total_done = sum(end - start for start, end in self.task_done_time)
            self.work_remaining = max(0, self.task_duration - total_done)
        else:
            # Update work remaining if we made progress last step
            if last_cluster_type in [ClusterType.SPOT, ClusterType.ON_DEMAND]:
                self.work_remaining = max(0, self.work_remaining - self.step_size)
        
        # Update overhead counter
        if self.overhead_remaining > 0:
            self.overhead_remaining -= 1
        
        # Track spot availability pattern
        if has_spot:
            self.spot_unavailable_count = 0
        else:
            self.spot_unavailable_count += 1
        
        # Track consecutive spot work
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.consecutive_spot_work += 1
        else:
            self.consecutive_spot_work = 0
        
        # Update risk factor based on progress
        time_used = self.current_step / self.steps_per_hour
        time_remaining = 70 - time_used
        work_needed_hours = self.work_remaining / 3600
        
        if time_remaining > 0:
            required_rate = work_needed_hours / time_remaining
            # Higher required rate means more risk-averse
            self.risk_factor = min(2.0, max(1.0, required_rate * 1.5))
    
    def _calculate_safe_threshold(self) -> float:
        """Calculate how conservative to be based on remaining time"""
        time_used_hours = self.current_step / self.steps_per_hour
        time_remaining_hours = 70 - time_used_hours
        work_needed_hours = self.work_remaining / 3600
        
        if time_remaining_hours <= 0 or work_needed_hours <= 0:
            return 0.0
        
        # Safety margin: ensure we finish with buffer
        safety_buffer = 2.0  # hours
        available_time = time_remaining_hours - safety_buffer
        
        if available_time <= 0:
            return 1.0  # Must use on-demand
        
        required_rate = work_needed_hours / available_time
        
        # Normalize to 0-1 range
        normalized_rate = min(1.0, max(0.0, (required_rate - 0.5) * 2.0))
        return normalized_rate
    
    def _should_use_spot(self, has_spot: bool) -> bool:
        """Decide whether to use spot based on current conditions"""
        if not has_spot:
            return False
        
        # Can't use spot during overhead
        if self.overhead_remaining > 0:
            return False
        
        # Calculate conservative threshold
        conservative = self._calculate_safe_threshold()
        
        # Adjust based on spot pattern
        spot_reliability = 1.0
        if len(self.spot_usage_history) > 10:
            recent_available = sum(self.spot_usage_history[-10:]) / 10.0
            spot_reliability = recent_available
        
        # Use spot if conditions are favorable enough
        use_spot_score = (1.0 - conservative) * spot_reliability
        
        # Minimum threshold to use spot
        return use_spot_score > 0.3
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state
        self._update_state(last_cluster_type, has_spot)
        
        # Record spot availability
        self.spot_usage_history.append(1 if has_spot else 0)
        if len(self.spot_usage_history) > 100:
            self.spot_usage_history.pop(0)
        
        # Check if we're done
        if self.work_remaining <= 0:
            return ClusterType.NONE
        
        # Check if we need to switch to on-demand due to overhead
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.overhead_remaining = self.overhead_steps
        
        # Determine if we should use spot
        use_spot = self._should_use_spot(has_spot)
        
        # Calculate remaining steps needed
        steps_needed = math.ceil(self.work_remaining / self.step_size)
        steps_remaining = self.deadline_steps - self.current_step
        
        # Emergency mode: must use on-demand to finish
        if steps_needed > steps_remaining * 0.9:  # 90% of remaining time
            return ClusterType.ON_DEMAND
        
        # If we have overhead and little time, use on-demand to avoid overhead
        if self.overhead_remaining > 0 and steps_needed > steps_remaining - self.overhead_steps:
            return ClusterType.ON_DEMAND
        
        if use_spot:
            return ClusterType.SPOT
        elif steps_needed > steps_remaining * 0.7:  # 70% threshold
            return ClusterType.ON_DEMAND
        else:
            # Pause if we have time buffer
            return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
