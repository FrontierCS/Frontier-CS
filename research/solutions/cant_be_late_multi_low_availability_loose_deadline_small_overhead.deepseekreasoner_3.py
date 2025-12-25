import json
from argparse import Namespace
import heapq
from typing import List, Tuple
from enum import Enum

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "efficient_multi_region"

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
        
        # Additional initialization
        self.num_regions = None
        self.spot_prices = [0.9701, 0.9701, 0.9701, 0.9701, 0.9701, 0.9701, 0.9701, 0.9701]
        self.ondemand_prices = [3.06, 3.06, 3.06, 3.06, 3.06, 3.06, 3.06, 3.06]
        self.region_history = []  # Track region availability
        self.consecutive_spot_failures = 0
        self.last_decision = ClusterType.NONE
        self.time_since_switch = 0
        self.current_region_spot_reliability = 1.0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if self.num_regions is None:
            self.num_regions = self.env.get_num_regions()
        
        # Update region history
        current_region = self.env.get_current_region()
        if len(self.region_history) <= current_region:
            self.region_history.extend([[] for _ in range(current_region - len(self.region_history) + 1)])
        self.region_history[current_region].append(has_spot)
        
        # Calculate key metrics
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        total_work_needed = self.task_duration
        work_done = sum(self.task_done_time)
        work_remaining = total_work_needed - work_done
        time_remaining = deadline - elapsed
        overhead = self.restart_overhead
        
        # If no work remaining, just return NONE
        if work_remaining <= 0:
            return ClusterType.NONE
            
        # Calculate minimum time needed
        min_time_needed = work_remaining
        if self.remaining_restart_overhead > 0:
            min_time_needed += self.remaining_restart_overhead
        
        # If we can't possibly finish, use on-demand as last resort
        if time_remaining < min_time_needed:
            return ClusterType.ON_DEMAND
        
        # Calculate slack ratio
        slack_ratio = time_remaining / min_time_needed if min_time_needed > 0 else float('inf')
        
        # Update consecutive spot failure counter
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = 0
        
        # Update current region reliability (using recent history)
        recent_history = self.region_history[current_region][-10:]  # Last 10 steps
        if recent_history:
            self.current_region_spot_reliability = sum(recent_history) / len(recent_history)
        
        # Calculate effective cost considering reliability
        effective_spot_cost = self.spot_prices[current_region] / max(self.current_region_spot_reliability, 0.1)
        
        # Decision logic
        decision = self._make_decision(
            work_remaining=work_remaining,
            time_remaining=time_remaining,
            slack_ratio=slack_ratio,
            has_spot=has_spot,
            effective_spot_cost=effective_spot_cost,
            ondemand_cost=self.ondemand_prices[current_region],
            current_region=current_region
        )
        
        # Consider region switching if spot is unavailable
        if decision == ClusterType.SPOT and not has_spot:
            decision = self._consider_region_switch(
                current_region=current_region,
                work_remaining=work_remaining,
                time_remaining=time_remaining,
                slack_ratio=slack_ratio
            )
        
        # Update last decision
        self.last_decision = decision
        self.time_since_switch += self.env.gap_seconds
        
        return decision

    def _make_decision(
        self,
        work_remaining: float,
        time_remaining: float,
        slack_ratio: float,
        has_spot: bool,
        effective_spot_cost: float,
        ondemand_cost: float,
        current_region: int
    ) -> ClusterType:
        """
        Core decision making logic.
        """
        # Calculate time pressure factor
        time_pressure = 1.0 - (time_remaining / self.deadline)
        
        # Calculate work pressure factor
        work_pressure = 1.0 - (work_remaining / self.task_duration)
        
        # Base thresholds
        spot_threshold = 0.3
        ondemand_threshold = 0.8
        
        # Adjust thresholds based on time pressure
        if time_pressure > 0.7:
            spot_threshold = 0.1
            ondemand_threshold = 0.5
        elif time_pressure > 0.5:
            spot_threshold = 0.2
            ondemand_threshold = 0.6
        
        # Check if we should use on-demand due to time pressure
        if slack_ratio < 1.5:
            return ClusterType.ON_DEMAND
        
        # Check if we should use on-demand due to low reliability
        if self.current_region_spot_reliability < 0.3 and self.consecutive_spot_failures > 2:
            return ClusterType.ON_DEMAND
        
        # Calculate cost benefit
        cost_ratio = effective_spot_cost / ondemand_cost
        
        # If spot is significantly cheaper and available, use it
        if has_spot and cost_ratio < 0.5 and slack_ratio > 2.0:
            return ClusterType.SPOT
        
        # If spot is available and we have reasonable slack
        if has_spot and slack_ratio > 1.8:
            return ClusterType.SPOT
        
        # If we have plenty of time and spot is available
        if has_spot and slack_ratio > 3.0:
            return ClusterType.SPOT
        
        # Default to on-demand if we're running out of time
        if slack_ratio < 2.0:
            return ClusterType.ON_DEMAND
        
        # If spot not available and we have time, wait
        if not has_spot and slack_ratio > 2.5:
            return ClusterType.NONE
        
        # Default to on-demand
        return ClusterType.ON_DEMAND

    def _consider_region_switch(
        self,
        current_region: int,
        work_remaining: float,
        time_remaining: float,
        slack_ratio: float
    ) -> ClusterType:
        """
        Consider switching to a region with better spot availability.
        """
        if self.num_regions <= 1:
            return ClusterType.ON_DEMAND
        
        # Don't switch too frequently
        if self.time_since_switch < 3600:  # 1 hour
            if slack_ratio > 2.0:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        
        # Find best region to switch to
        best_region = current_region
        best_reliability = self.current_region_spot_reliability
        
        for region in range(self.num_regions):
            if region == current_region:
                continue
                
            # Estimate reliability based on history
            region_reliability = 0.5  # Default estimate
            
            if len(self.region_history) > region and self.region_history[region]:
                recent = self.region_history[region][-5:]  # Last 5 steps
                if recent:
                    region_reliability = sum(recent) / len(recent)
            
            if region_reliability > best_reliability * 1.2:  # 20% better
                best_region = region
                best_reliability = region_reliability
        
        # Switch if we found a significantly better region
        if best_region != current_region and slack_ratio > 1.8:
            self.env.switch_region(best_region)
            self.time_since_switch = 0
            self.current_region_spot_reliability = best_reliability
            
            # After switching, try to use spot if we think it's available
            # (We don't know for sure, so we'll be conservative)
            if best_reliability > 0.6:
                return ClusterType.SPOT
            elif slack_ratio > 2.5:
                return ClusterType.NONE
        
        # If not switching, decide based on slack
        if slack_ratio > 2.5:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND
