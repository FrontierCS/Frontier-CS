import json
from argparse import Namespace
from typing import List
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "efficient_scheduler"

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
        
        # Initialize state
        self.region_history = {}
        self.last_decision = ClusterType.NONE
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.ondemand_price / self.spot_price
        self.critical_threshold = 0.7  # When to be conservative
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed
        
        # If work is done, return NONE
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Emergency mode: must use on-demand to meet deadline
        if time_left <= remaining_work + self.restart_overhead:
            # Check if we're already running on-demand
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                # Switch to on-demand
                return ClusterType.ON_DEMAND
        
        # Calculate progress percentage
        progress = work_done / self.task_duration
        time_progress = time_elapsed / self.deadline
        
        # Critical phase - be more conservative
        is_critical = (time_progress > self.critical_threshold) or (progress < time_progress * 0.8)
        
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Track region history for spot reliability
        if current_region not in self.region_history:
            self.region_history[current_region] = {
                'spot_available_count': 0,
                'total_count': 0
            }
        
        self.region_history[current_region]['total_count'] += 1
        if has_spot:
            self.region_history[current_region]['spot_available_count'] += 1
        
        # Calculate spot reliability for current region
        region_data = self.region_history[current_region]
        spot_reliability = (region_data['spot_available_count'] / 
                           max(region_data['total_count'], 1))
        
        # If we're in a restart overhead period, wait or use on-demand
        if self.remaining_restart_overhead > 0:
            if is_critical or time_left < remaining_work + 2 * self.restart_overhead:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
        
        # Decision logic
        if has_spot:
            # Use spot if available and conditions are favorable
            if not is_critical and spot_reliability > 0.5:
                # Stay with spot if we were already using it
                if last_cluster_type == ClusterType.SPOT:
                    return ClusterType.SPOT
                # Consider switching to spot
                elif (remaining_work > self.env.gap_seconds * 2 and 
                      time_left > remaining_work * 1.5):
                    return ClusterType.SPOT
                else:
                    # For short remaining work, stay with current type
                    if last_cluster_type == ClusterType.ON_DEMAND:
                        return ClusterType.ON_DEMAND
                    else:
                        return ClusterType.NONE
            else:
                # In critical phase or unreliable spot, use on-demand
                return ClusterType.ON_DEMAND
        else:
            # No spot available in current region
            if is_critical or time_left < remaining_work * 1.2:
                # Must use on-demand in critical phase
                return ClusterType.ON_DEMAND
            else:
                # Try switching to another region
                best_region = current_region
                best_reliability = spot_reliability
                
                for region_idx in range(num_regions):
                    if region_idx == current_region:
                        continue
                    
                    if region_idx in self.region_history:
                        reg_data = self.region_history[region_idx]
                        reg_reliability = (reg_data['spot_available_count'] / 
                                          max(reg_data['total_count'], 1))
                    else:
                        # If we have no history, assume average
                        reg_reliability = 0.5
                    
                    if reg_reliability > best_reliability:
                        best_reliability = reg_reliability
                        best_region = region_idx
                
                if best_region != current_region and best_reliability > 0.3:
                    # Switch to better region
                    self.env.switch_region(best_region)
                    return ClusterType.NONE
                else:
                    # Stay and use on-demand if needed
                    if last_cluster_type == ClusterType.ON_DEMAND:
                        return ClusterType.ON_DEMAND
                    else:
                        # Wait for spot to become available
                        return ClusterType.NONE

    def _should_switch_region(self, current_region: int, has_spot: bool) -> bool:
        """Helper to decide if we should switch regions."""
        if has_spot:
            return False
        
        # Only consider switching if we're not in critical time
        time_elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_left = self.deadline - time_elapsed
        
        if time_left < remaining_work * 1.5:
            return False
        
        # Check if other regions might be better
        num_regions = self.env.get_num_regions()
        if num_regions <= 1:
            return False
        
        return True
