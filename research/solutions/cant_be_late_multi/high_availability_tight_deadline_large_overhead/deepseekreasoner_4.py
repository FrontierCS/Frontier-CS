import json
from argparse import Namespace
import math
from typing import List
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        
        # Initialize strategy state
        self.spot_history = []
        self.last_spot_available = False
        self.consecutive_spot_failures = 0
        self.region_stability = {}
        self.current_region = 0
        self.best_region = 0
        self.spot_attempts = 0
        self.on_demand_fallback = False
        self.time_since_last_switch = 0
        self.min_region_stay = 3  # minimum steps to stay in a region
        
        return self

    def _should_switch_region(self, current_region: int, has_spot: bool) -> bool:
        """Determine if we should switch to another region."""
        if self.time_since_last_switch < self.min_region_stay:
            return False
            
        num_regions = self.env.get_num_regions()
        if num_regions <= 1:
            return False
            
        # Calculate time pressure
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        time_pressure = remaining_work / max(remaining_time, 0.1)
        
        # If no spot in current region and we have time pressure, consider switching
        if not has_spot and time_pressure > 0.7:
            return True
            
        # If we've had consecutive spot failures
        if self.consecutive_spot_failures >= 3:
            return True
            
        return False

    def _choose_best_region(self) -> int:
        """Choose the best region based on stability history."""
        num_regions = self.env.get_num_regions()
        if not self.region_stability:
            return (self.current_region + 1) % num_regions
            
        # Find region with best stability score
        best_score = -1
        best_region = self.current_region
        
        for region in range(num_regions):
            if region == self.current_region:
                continue
                
            stability = self.region_stability.get(region, 0.5)
            if stability > best_score:
                best_score = stability
                best_region = region
                
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update region history
        current_region = self.env.get_current_region()
        if current_region not in self.region_stability:
            self.region_stability[current_region] = 0.5
        
        # Update spot history
        self.spot_history.append(has_spot)
        if len(self.spot_history) > 10:
            self.spot_history.pop(0)
            
        # Update consecutive spot failures
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
        
        # Update region stability based on spot availability
        spot_ratio = sum(self.spot_history) / max(len(self.spot_history), 1)
        self.region_stability[current_region] = 0.9 * self.region_stability[current_region] + 0.1 * spot_ratio
        
        # Calculate remaining work and time
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # Safety margin: start using on-demand if we're running out of time
        time_per_step = self.env.gap_seconds
        steps_needed_on_demand = math.ceil(remaining_work / time_per_step)
        steps_available = remaining_time / time_per_step
        
        # Critical condition: must use on-demand to finish on time
        critical_condition = (
            steps_available < steps_needed_on_demand + 2 or
            remaining_time < remaining_work + 2 * self.restart_overhead
        )
        
        # Handle region switching
        if self._should_switch_region(current_region, has_spot):
            best_region = self._choose_best_region()
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.current_region = best_region
                self.time_since_last_switch = 0
                self.spot_history = []
                self.consecutive_spot_failures = 0
                # When switching, use on-demand for stability
                return ClusterType.ON_DEMAND
        
        self.time_since_last_switch += 1
        
        # Decision logic
        if critical_condition:
            # Must finish, use on-demand
            return ClusterType.ON_DEMAND
            
        elif has_spot and not self.on_demand_fallback:
            # Use spot if available and we're not in fallback mode
            # Check if spot has been reliable recently
            recent_reliability = sum(self.spot_history[-3:]) if len(self.spot_history) >= 3 else 1.0
            
            if recent_reliability >= 2:  # At least 2 out of last 3 steps had spot
                self.spot_attempts += 1
                # After too many spot attempts, consider temporary fallback
                if self.spot_attempts > 20 and self.consecutive_spot_failures > 2:
                    self.on_demand_fallback = True
                    self.spot_attempts = 0
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT
            else:
                # Spot not reliable recently, use on-demand temporarily
                self.on_demand_fallback = True
                return ClusterType.ON_DEMAND
                
        elif self.on_demand_fallback:
            # We're in fallback mode, check if we should try spot again
            if has_spot and self.consecutive_spot_failures == 0:
                self.on_demand_fallback = False
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
            
        else:
            # No spot available and not critical
            return ClusterType.ON_DEMAND