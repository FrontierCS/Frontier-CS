import argparse
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import math

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args=None):
        super().__init__(args)
        self.spot_unavailable_start = None
        self.consecutive_spot_failures = 0
        self.max_spot_failures_before_switch = 3
        self.min_spot_available_time = 3600  # 1 hour minimum
        self.safety_margin = 3600 * 2  # 2 hours safety margin
        
    def solve(self, spec_path: str) -> "Solution":
        # Read configuration if needed
        try:
            with open(spec_path, 'r') as f:
                # Parse any custom configuration
                pass
        except:
            pass
        return self
    
    def _calculate_time_needed(self, use_spot: bool) -> float:
        """Calculate time needed to complete remaining work with given strategy"""
        if len(self.task_done_time) == 0:
            remaining = self.task_duration
        else:
            total_done = sum(end - start for start, end in self.task_done_time)
            remaining = self.task_duration - total_done
        
        if use_spot:
            # Account for potential restart overheads
            overhead_factor = 1.1  # 10% buffer for restarts
            return remaining * overhead_factor
        else:
            return remaining
    
    def _get_remaining_time(self) -> float:
        """Get remaining time before deadline"""
        return self.deadline - self.env.elapsed_seconds
    
    def _should_use_ondemand(self, has_spot: bool) -> bool:
        """Decide if we should use on-demand based on time constraints"""
        remaining_time = self._get_remaining_time()
        
        # Calculate time needed with different strategies
        time_needed_ondemand = self._calculate_time_needed(use_spot=False)
        time_needed_spot = self._calculate_time_needed(use_spot=True)
        
        # If we're running out of time, switch to on-demand
        time_critical = remaining_time < time_needed_ondemand + self.safety_margin
        
        # If spot has been unreliable recently
        spot_unreliable = self.consecutive_spot_failures >= self.max_spot_failures_before_switch
        
        # If spot is not available
        if not has_spot:
            return True
            
        return time_critical or spot_unreliable
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update spot failure tracking
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
            if self.spot_unavailable_start is None:
                self.spot_unavailable_start = self.env.elapsed_seconds
        elif has_spot:
            self.consecutive_spot_failures = 0
            self.spot_unavailable_start = None
        
        # Calculate remaining work percentage
        total_done = sum(end - start for start, end in self.task_done_time)
        progress = total_done / self.task_duration if self.task_duration > 0 else 0
        remaining_work = self.task_duration - total_done
        
        # Get remaining time
        remaining_time = self._get_remaining_time()
        
        # Check if we should use on-demand
        if self._should_use_ondemand(has_spot):
            return ClusterType.ON_DEMAND
        
        # If we have plenty of time and spot is available, use spot
        if has_spot and remaining_time > self._calculate_time_needed(use_spot=True) + self.safety_margin:
            # Check if we've had spot available for a while
            if self.spot_unavailable_start is not None:
                spot_available_duration = self.env.elapsed_seconds - self.spot_unavailable_start
                if spot_available_duration < self.min_spot_available_time:
                    # Wait a bit longer to ensure spot stability
                    return ClusterType.NONE
            
            # Check if we're close to completing a work segment
            # This helps minimize restart overheads
            if last_cluster_type == ClusterType.NONE and remaining_work > self.env.gap_seconds * 2:
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            else:
                # Transition from on-demand to spot
                return ClusterType.SPOT
        
        # Conservative approach: if we're not sure, use on-demand
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
