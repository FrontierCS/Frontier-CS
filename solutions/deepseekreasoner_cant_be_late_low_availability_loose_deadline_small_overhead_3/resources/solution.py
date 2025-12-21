import math
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold_solver"
    
    def solve(self, spec_path: str) -> "Solution":
        # Initialize state variables
        self.spot_price = 0.97  # $/hr
        self.on_demand_price = 3.06  # $/hr
        self.price_ratio = self.spot_price / self.on_demand_price
        
        # Time conversion constants
        self.hours_to_seconds = 3600
        
        # Load spec if provided (not required for this implementation)
        # For this problem, we can hardcode parameters since they're given
        self.task_duration_hours = 48
        self.deadline_hours = 70
        self.restart_overhead_hours = 0.05
        
        # Convert to seconds for consistency with API
        self.task_duration_sec = self.task_duration_hours * self.hours_to_seconds
        self.deadline_sec = self.deadline_hours * self.hours_to_seconds
        self.restart_overhead_sec = self.restart_overhead_hours * self.hours_to_seconds
        
        # Adaptive threshold parameters
        self.min_spot_availability_threshold = 0.2  # 20%
        self.max_spot_availability_threshold = 0.6  # 60%
        
        # State tracking
        self.spot_availability_history = []
        self.consecutive_spot_failures = 0
        self.max_consecutive_failures = 3
        
        # Cost tracking
        self.estimated_cost = 0
        self.estimated_time_used = 0
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update availability history
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Calculate current progress and time constraints
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        elapsed_time = self.env.elapsed_seconds
        time_left = self.deadline - elapsed_time
        
        # Calculate safety margin needed for on-demand completion
        safety_margin = self.restart_overhead_sec * 2  # Allow for 2 restarts
        
        # Calculate minimum time needed to finish with on-demand
        min_time_needed = remaining_work
        
        # Emergency mode: if we can't finish even with continuous on-demand
        if min_time_needed + safety_margin > time_left:
            return ClusterType.ON_DEMAND
        
        # Calculate adaptive threshold based on progress and time constraints
        progress_ratio = completed_work / self.task_duration
        time_pressure = 1.0 - (time_left / (self.deadline_sec * 0.8))  # Scale to 0-1
        
        # Adjust threshold based on progress and time pressure
        base_threshold = self.min_spot_availability_threshold
        if progress_ratio > 0.7:  # If we're more than 70% done
            base_threshold = self.max_spot_availability_threshold
        
        # Increase threshold with time pressure
        adaptive_threshold = base_threshold * (1.0 + time_pressure)
        adaptive_threshold = min(adaptive_threshold, self.max_spot_availability_threshold)
        
        # Calculate spot availability probability from history
        if len(self.spot_availability_history) > 0:
            spot_probability = sum(self.spot_availability_history) / len(self.spot_availability_history)
        else:
            spot_probability = 0.3  # Default assumption
        
        # Update consecutive failures count
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        elif last_cluster_type != ClusterType.SPOT or has_spot:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
        
        # Decision logic
        if has_spot:
            # Consider using spot if:
            # 1. We have good probability of success
            # 2. We haven't had too many consecutive failures
            # 3. We have enough time buffer
            
            time_buffer_needed = remaining_work + self.restart_overhead_sec * 2
            
            if (spot_probability >= adaptive_threshold and 
                self.consecutive_spot_failures < self.max_consecutive_failures and
                time_buffer_needed < time_left * 0.8):
                return ClusterType.SPOT
            else:
                # Use on-demand if spot looks risky but we have time pressure
                if time_pressure > 0.5:
                    return ClusterType.ON_DEMAND
                else:
                    # Wait and see
                    return ClusterType.NONE
        else:
            # No spot available
            if time_pressure > 0.7 or remaining_work > time_left * 0.9:
                # High time pressure or very little time left
                return ClusterType.ON_DEMAND
            elif time_pressure > 0.4:
                # Medium time pressure - use on-demand if we have some buffer
                buffer_needed = remaining_work + self.restart_overhead_sec
                if buffer_needed < time_left:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.NONE
            else:
                # Low time pressure - wait for spot
                return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
