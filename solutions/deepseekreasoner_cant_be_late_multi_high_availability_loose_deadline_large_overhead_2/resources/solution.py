import json
from argparse import Namespace
from typing import List
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "adaptive_hedging"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)
        
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        # Initialize state tracking
        self.last_region = -1
        self.region_spot_history = {}
        self.region_availability_score = {}
        self.consecutive_failures = 0
        self.consecutive_spot = 0
        self.current_region_spot_streak = 0
        
        # Constants
        self.SPOT_PRICE = 0.9701
        self.ON_DEMAND_PRICE = 3.06
        self.SAFETY_MARGIN = 0.1  # 10% safety margin for deadline
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Update region tracking
        if current_region != self.last_region:
            self.last_region = current_region
            self.current_region_spot_streak = 0
            self.consecutive_failures = 0
        
        # Update region availability history
        if current_region not in self.region_spot_history:
            self.region_spot_history[current_region] = []
        
        self.region_spot_history[current_region].append(has_spot)
        if len(self.region_spot_history[current_region]) > 10:
            self.region_spot_history[current_region].pop(0)
        
        # Calculate availability score for current region
        if len(self.region_spot_history[current_region]) > 0:
            recent_history = self.region_spot_history[current_region][-5:] if len(
                self.region_spot_history[current_region]) >= 5 else self.region_spot_history[current_region]
            self.region_availability_score[current_region] = sum(recent_history) / len(recent_history)
        
        # Update streaks
        if has_spot and last_cluster_type == ClusterType.SPOT:
            self.current_region_spot_streak += 1
            self.consecutive_spot += 1
            self.consecutive_failures = 0
        elif not has_spot and last_cluster_type == ClusterType.SPOT:
            self.consecutive_failures += 1
            self.consecutive_spot = 0
            self.current_region_spot_streak = 0
        
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        remaining_time = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Calculate effective work per time unit for each option
        effective_spot_work = gap - (self.restart_overhead if last_cluster_type != ClusterType.SPOT else 0)
        effective_ondemand_work = gap - (self.restart_overhead if last_cluster_type != ClusterType.ON_DEMAND else 0)
        
        # Calculate minimum required rate
        required_rate = remaining_work / remaining_time if remaining_time > 0 else float('inf')
        
        # If we're very close to deadline, use on-demand
        if remaining_time < self.restart_overhead * 2:
            return ClusterType.ON_DEMAND
        
        # Calculate confidence in spot availability
        spot_confidence = 0.5
        if current_region in self.region_availability_score:
            spot_confidence = self.region_availability_score[current_region]
        
        # Adjust confidence based on streak
        if self.current_region_spot_streak > 3:
            spot_confidence = min(1.0, spot_confidence + 0.2)
        
        # Calculate risk-adjusted expected work for spot
        expected_spot_work = spot_confidence * effective_spot_work
        
        # Determine if we should switch regions
        should_switch = False
        switch_target = current_region
        
        if not has_spot or self.consecutive_failures > 1:
            # Consider switching to a region with better history
            best_region = current_region
            best_score = spot_confidence
            
            for region in range(num_regions):
                if region == current_region:
                    continue
                
                region_score = self.region_availability_score.get(region, 0.5)
                if region_score > best_score:
                    best_score = region_score
                    best_region = region
            
            if best_region != current_region and best_score > spot_confidence + 0.1:
                should_switch = True
                switch_target = best_region
        
        # If we need to switch regions, do it now
        if should_switch:
            self.env.switch_region(switch_target)
            # After switching, we'll pay overhead anyway, so use on-demand if we're time-constrained
            if remaining_time < remaining_work / (gap - self.restart_overhead) * 1.5:
                return ClusterType.ON_DEMAND
            # Otherwise try spot in new region
            return ClusterType.SPOT
        
        # Decision logic based on remaining time and work
        time_per_spot_unit = gap / expected_spot_work if expected_spot_work > 0 else float('inf')
        time_per_ondemand_unit = gap / effective_ondemand_work
        
        # Calculate how much time we would need with each strategy
        time_needed_spot = remaining_work / expected_spot_work * gap if expected_spot_work > 0 else float('inf')
        time_needed_ondemand = remaining_work / effective_ondemand_work * gap
        
        # Add safety margin
        safe_remaining_time = remaining_time * (1 - self.SAFETY_MARGIN)
        
        # If on-demand is the only way to meet deadline with safety margin
        if time_needed_ondemand < safe_remaining_time <= time_needed_spot:
            return ClusterType.ON_DEMAND
        
        # If both can meet deadline, choose based on cost-effectiveness
        if time_needed_spot < safe_remaining_time and time_needed_ondemand < safe_remaining_time:
            # Calculate expected cost for remaining work
            spot_attempts = remaining_work / expected_spot_work if expected_spot_work > 0 else float('inf')
            ondemand_attempts = remaining_work / effective_ondemand_work
            
            spot_cost = spot_attempts * gap / 3600 * self.SPOT_PRICE
            ondemand_cost = ondemand_attempts * gap / 3600 * self.ON_DEMAND_PRICE
            
            # Use spot if it's significantly cheaper and we have confidence
            if spot_cost * 1.5 < ondemand_cost and spot_confidence > 0.6:
                if has_spot:
                    return ClusterType.SPOT
                else:
                    # If spot not available but we wanted it, use on-demand
                    return ClusterType.ON_DEMAND
            else:
                # More conservative: use on-demand
                return ClusterType.ON_DEMAND
        
        # If we're ahead of schedule and spot is available, use it
        if remaining_time > time_needed_spot * 1.5:
            if has_spot:
                return ClusterType.SPOT
            elif self.consecutive_failures < 2:
                # Wait for spot to come back
                return ClusterType.NONE
            else:
                # Switch to on-demand if spot keeps failing
                return ClusterType.ON_DEMAND
        
        # Default fallback: use on-demand if spot not available, otherwise use spot
        if has_spot and spot_confidence > 0.3:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND
