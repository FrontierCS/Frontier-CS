import json
from argparse import Namespace
from typing import List
import math

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
        
        # Additional initialization
        self.region_stats = []
        self.last_spot_check = -1
        self.consecutive_spot_failures = 0
        self.max_spot_failures = 3
        self.switch_cooldown = 0
        self.last_region = -1
        self.region_attempts = []
        self.current_strategy = "aggressive"  # "aggressive", "conservative", "panic"
        
        return self

    def _update_strategy_state(self):
        """Update strategy based on current progress and time"""
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        if remaining_time <= 0:
            return
        
        # Calculate how much work we need to do per remaining time
        work_per_time_needed = remaining_work / remaining_time if remaining_time > 0 else float('inf')
        
        # Check if we're falling behind
        if work_per_time_needed > 1.0:
            self.current_strategy = "panic"
        elif work_per_time_needed > 0.8:
            self.current_strategy = "conservative"
        else:
            self.current_strategy = "aggressive"

    def _find_best_region(self, current_region: int, has_spot: bool) -> int:
        """Find the best region to switch to"""
        num_regions = self.env.get_num_regions()
        
        # If we haven't explored much, try a new region
        if len(self.region_attempts) < num_regions:
            for i in range(num_regions):
                if i not in self.region_attempts:
                    return i
        
        # If current region has spot and we haven't had many failures, stay
        if has_spot and self.consecutive_spot_failures < 2:
            return current_region
            
        # Otherwise, try to find a region we haven't visited recently
        # Start from current+1 to avoid immediate switching back
        for offset in range(1, num_regions):
            next_region = (current_region + offset) % num_regions
            if next_region != self.last_region:
                return next_region
                
        return current_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update strategy based on current progress
        self._update_strategy_state()
        
        # Track current region
        current_region = self.env.get_current_region()
        if current_region not in self.region_attempts:
            self.region_attempts.append(current_region)
        
        # Handle cooldown for switching
        if self.switch_cooldown > 0:
            self.switch_cooldown -= 1
            
        # Calculate remaining work and time
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # If no work left, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If no time left, panic mode - use on-demand
        if remaining_time <= self.env.gap_seconds * 2:
            return ClusterType.ON_DEMAND
            
        # Check if we're in overhead period
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
            
        # Strategy decision
        if self.current_strategy == "panic":
            # In panic mode, use on-demand to ensure progress
            if last_cluster_type != ClusterType.ON_DEMAND:
                # Switching to on-demand incurs overhead but guarantees progress
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
                
        elif self.current_strategy == "conservative":
            # Conservative: prefer on-demand but try spot if available and we have time
            time_per_work_unit = remaining_time / remaining_work if remaining_work > 0 else float('inf')
            
            if time_per_work_unit < 1.5:  # Tight schedule
                return ClusterType.ON_DEMAND
            elif has_spot and self.consecutive_spot_failures < 2:
                # Try spot if we haven't failed too much recently
                if last_cluster_type == ClusterType.SPOT:
                    return ClusterType.SPOT
                else:
                    # Consider overhead for switching to spot
                    effective_work = self.env.gap_seconds - self.restart_overhead
                    if effective_work > 0 and remaining_time > self.restart_overhead * 2:
                        return ClusterType.SPOT
                    else:
                        return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
                
        else:  # aggressive strategy
            # Aggressive: prefer spot to minimize cost
            
            # Update spot failure tracking
            if last_cluster_type == ClusterType.SPOT and not has_spot:
                self.consecutive_spot_failures += 1
            else:
                self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
            
            # Check if we should switch regions
            best_region = self._find_best_region(current_region, has_spot)
            should_switch = (best_region != current_region and 
                           self.switch_cooldown == 0 and
                           self.consecutive_spot_failures >= 2)
            
            if should_switch:
                self.env.switch_region(best_region)
                self.switch_cooldown = 3  # Don't switch again for a few steps
                self.last_region = current_region
                self.consecutive_spot_failures = 0
                # After switching, we need to wait due to overhead
                return ClusterType.NONE
            
            # Use spot if available and we haven't failed too much
            if has_spot and self.consecutive_spot_failures < self.max_spot_failures:
                # Check if we have enough time for potential overhead
                if remaining_time > self.restart_overhead * 3:
                    return ClusterType.SPOT
                else:
                    # Not enough time for risks
                    return ClusterType.ON_DEMAND
            else:
                # No spot available or too many failures
                if remaining_time > self.env.gap_seconds * 3:  # We have some time
                    # Try switching region next time
                    self.consecutive_spot_failures = min(
                        self.consecutive_spot_failures + 1, 
                        self.max_spot_failures + 1
                    )
                    return ClusterType.NONE
                else:
                    # Running out of time, use on-demand
                    return ClusterType.ON_DEMAND