import json
from argparse import Namespace
from enum import Enum
from typing import List
import math

class ClusterType(Enum):
    SPOT = 1
    ON_DEMAND = 2
    NONE = 3

class Solution:
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        
        # Initialize base strategy
        super().__init__(args)
        
        # Store configuration
        self.regions = []
        self.region_history = {}
        self.current_region = 0
        self.consecutive_failures = 0
        self.last_action = ClusterType.NONE
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Get current region if available
        try:
            self.current_region = self.env.get_current_region()
        except:
            self.current_region = 0
            
        # Calculate remaining work and time
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        remaining_work = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # If no work left, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # Calculate effective time needed considering restart overhead
        effective_work_needed = remaining_work
        if (last_cluster_type != ClusterType.NONE and 
            self.last_action != last_cluster_type and 
            self.last_action != ClusterType.NONE):
            effective_work_needed += self.restart_overhead
            
        # Critical time check: if we're running out of time, use on-demand
        time_needed_on_demand = effective_work_needed
        spot_price_ratio = 0.9701 / 3.06  # Spot is about 31.7% of on-demand cost
        
        # Calculate conservative time estimate for spot (accounting for potential interruptions)
        spot_safety_factor = 1.5
        time_needed_spot = effective_work_needed * spot_safety_factor
        
        # If time is very critical, use on-demand
        if time_remaining < time_needed_on_demand * 1.1:
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
            
        # If spot is available and we have reasonable time buffer, use spot
        if has_spot and time_remaining > time_needed_spot:
            self.last_action = ClusterType.SPOT
            return ClusterType.SPOT
            
        # If spot is not available but we have time, consider switching regions
        num_regions = self.env.get_num_regions()
        if num_regions > 1 and time_remaining > time_needed_on_demand * 1.2:
            # Try switching to another region
            next_region = (self.current_region + 1) % num_regions
            try:
                self.env.switch_region(next_region)
                self.current_region = next_region
            except:
                pass
                
            # After switching, use spot if available, otherwise pause
            if has_spot:
                self.last_action = ClusterType.SPOT
                return ClusterType.SPOT
            else:
                self.last_action = ClusterType.NONE
                return ClusterType.NONE
                
        # Default to on-demand if we can't use spot and have time pressure
        if time_remaining > effective_work_needed:
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
            
        # If we're really out of time but still have work, try spot as last resort
        if has_spot:
            self.last_action = ClusterType.SPOT
            return ClusterType.SPOT
            
        # Final fallback
        self.last_action = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND