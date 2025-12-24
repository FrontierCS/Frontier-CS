import json
from argparse import Namespace
import math
from enum import Enum
from typing import List, Dict, Tuple
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cost_aware_deadline_strategy"

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
        super().__init__(args)
        
        # Store configuration
        self.total_work_needed = self.task_duration[0] * 3600  # Convert to seconds
        self.deadline_seconds = self.deadline
        self.overhead_seconds = self.restart_overhead[0] * 3600
        self.spot_price = 0.9701 / 3600  # $/second
        self.ondemand_price = 3.06 / 3600  # $/second
        
        # Initialize state tracking
        self.work_done = 0.0
        self.current_cost = 0.0
        self.last_action = None
        self.region_history = {}
        self.consecutive_spots = 0
        
        return self

    def _calculate_time_needed(self, remaining_work: float, use_ondemand: bool = False) -> float:
        """Calculate minimum time needed to finish remaining work."""
        if use_ondemand:
            # With on-demand, no interruptions
            return remaining_work
        else:
            # With spot, assume some interruptions
            return remaining_work + (self.overhead_seconds * 2)  # Conservative estimate

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Calculate remaining work and time
        if self.task_done_time:
            self.work_done = sum(self.task_done_time)
        else:
            self.work_done = 0.0
            
        remaining_work = self.total_work_needed - self.work_done
        time_left = self.deadline_seconds - self.env.elapsed_seconds
        
        # If work is done, return NONE
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # Calculate remaining time safety factor
        time_needed_ondemand = self._calculate_time_needed(remaining_work, True)
        time_needed_spot = self._calculate_time_needed(remaining_work, False)
        
        # Check if we're in critical time
        critical_time = time_left < time_needed_ondemand * 1.2
        
        # Track region performance
        current_region = self.env.get_current_region()
        if current_region not in self.region_history:
            self.region_history[current_region] = {
                'spot_availability': 0,
                'total_steps': 0,
                'successful_spots': 0
            }
        
        self.region_history[current_region]['total_steps'] += 1
        if has_spot:
            self.region_history[current_region]['spot_availability'] += 1
        
        # Strategy decision
        if critical_time:
            # Critical path: use on-demand to guarantee completion
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                # Switch to on-demand
                return ClusterType.ON_DEMAND
        else:
            # Non-critical path: optimize for cost
            if has_spot:
                # Check if we should explore other regions
                should_explore = False
                if self.consecutive_spots > 20:  # Been in spot too long, check other regions
                    best_region = current_region
                    best_availability = 0
                    
                    for region in range(self.env.get_num_regions()):
                        if region in self.region_history:
                            total = self.region_history[region]['total_steps']
                            avail = self.region_history[region]['spot_availability']
                            if total > 0 and (avail / total) > best_availability:
                                best_availability = avail / total
                                best_region = region
                    
                    if best_region != current_region:
                        self.env.switch_region(best_region)
                        self.consecutive_spots = 0
                        return ClusterType.NONE  # Pause for one step after switching
                
                # Use spot if available and we have time buffer
                time_buffer = time_left - time_needed_spot
                if time_buffer > self.overhead_seconds * 3:  # Conservative buffer
                    self.consecutive_spots += 1
                    return ClusterType.SPOT
                else:
                    # Not enough buffer, use on-demand
                    self.consecutive_spots = 0
                    return ClusterType.ON_DEMAND
            else:
                # No spot available, check other regions or use on-demand
                self.consecutive_spots = 0
                
                # Try to find a region with spot
                for region in range(self.env.get_num_regions()):
                    if region != current_region and region in self.region_history:
                        total = self.region_history[region]['total_steps']
                        avail = self.region_history[region]['spot_availability']
                        if total > 10 and (avail / total) > 0.5:  # Good history of spot availability
                            self.env.switch_region(region)
                            return ClusterType.NONE  # Pause for one step after switching
                
                # If we can't find good spot region and have time, use on-demand
                if time_left > time_needed_ondemand * 1.5:
                    # We have time, wait a bit for spot
                    return ClusterType.NONE
                else:
                    # Running out of time, use on-demand
                    return ClusterType.ON_DEMAND
