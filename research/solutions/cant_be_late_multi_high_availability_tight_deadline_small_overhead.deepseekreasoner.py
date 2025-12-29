import json
from argparse import Namespace
from typing import List, Tuple
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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
        
        # Initialize strategy parameters
        self.spot_price = 0.9701
        self.on_demand_price = 3.06
        self.price_ratio = self.spot_price / self.on_demand_price
        
        # Region tracking
        self.region_history = []
        self.region_spot_count = {}
        self.last_decision = None
        self.consecutive_spot_failures = 0
        self.switch_threshold = 3
        self.aggressiveness = 0.7  # Higher = more aggressive with spot
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Calculate remaining work and time
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        # If work is done, return NONE
        if remaining_work <= 1e-9:
            return ClusterType.NONE
        
        # Calculate time needed under different scenarios
        gap = self.env.gap_seconds
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Update region history and spot count
        self.region_history.append(current_region)
        if len(self.region_history) > 100:
            self.region_history.pop(0)
        
        if has_spot:
            self.region_spot_count[current_region] = self.region_spot_count.get(current_region, 0) + 1
        
        # Calculate conservative time estimates
        time_with_od = remaining_work
        if last_cluster_type != ClusterType.ON_DEMAND:
            time_with_od += self.restart_overhead
        
        # Calculate time with spot (accounting for potential failures)
        spot_success_prob = self.estimate_spot_success_probability(current_region, has_spot)
        expected_spot_time = remaining_work / max(spot_success_prob, 0.1)
        
        # Check if we're running out of time
        time_critical = remaining_time < time_with_od * 1.2
        
        # Determine best region for spot
        best_region = self.find_best_spot_region(current_region, has_spot)
        
        # Decision logic
        if time_critical:
            # Time is critical, use on-demand to guarantee completion
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        # If current region has spot and we're not in failure streak
        if has_spot and self.consecutive_spot_failures < self.switch_threshold:
            # Calculate risk-adjusted value
            risk_factor = min(1.0, remaining_time / (expected_spot_time * 1.5))
            
            # Use spot if it's sufficiently valuable
            spot_value = self.price_ratio * risk_factor * self.aggressiveness
            
            if spot_value > 0.5:  # Empirical threshold
                self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
                return ClusterType.SPOT
        
        # Check if we should switch regions
        if best_region != current_region and not time_critical:
            # Only switch if we have evidence the other region is better
            current_score = self.region_spot_count.get(current_region, 0)
            best_score = self.region_spot_count.get(best_region, 0)
            
            if best_score > current_score * 1.2:  # 20% better
                self.env.switch_region(best_region)
                # After switching, try spot if available
                if has_spot:
                    return ClusterType.SPOT
                else:
                    self.consecutive_spot_failures += 1
                    if self.consecutive_spot_failures >= self.switch_threshold:
                        return ClusterType.ON_DEMAND
                    return ClusterType.NONE
        
        # If spot not available or too risky, consider on-demand
        od_value = (1.0 - self.price_ratio) * (remaining_time / time_with_od)
        
        if od_value < 0.3 and not time_critical:  # On-demand not valuable enough
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
    
    def estimate_spot_success_probability(self, region: int, has_spot_now: bool) -> float:
        """Estimate probability of spot availability continuing."""
        if not has_spot_now:
            return 0.0
        
        # Simple estimation based on historical count
        total_steps = len(self.region_history)
        if total_steps == 0:
            return 0.5
        
        region_steps = sum(1 for r in self.region_history if r == region)
        if region_steps == 0:
            return 0.5
        
        spot_count = self.region_spot_count.get(region, 0)
        return spot_count / max(region_steps, 1)
    
    def find_best_spot_region(self, current_region: int, current_has_spot: bool) -> int:
        """Find the region with best spot availability."""
        num_regions = self.env.get_num_regions()
        
        # If current region has spot, stick with it
        if current_has_spot:
            return current_region
        
        # Otherwise, find region with highest spot count
        best_region = current_region
        best_score = self.region_spot_count.get(current_region, 0)
        
        for region in range(num_regions):
            if region == current_region:
                continue
            
            score = self.region_spot_count.get(region, 0)
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region