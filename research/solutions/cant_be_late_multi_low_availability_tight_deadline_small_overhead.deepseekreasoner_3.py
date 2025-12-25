import json
from argparse import Namespace
from enum import Enum
from typing import List, Tuple, Dict
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Action(Enum):
    SPOT = 0
    ON_DEMAND = 1
    NONE = 2
    SWITCH_SPOT = 3
    SWITCH_ON_DEMAND = 4


class Solution(MultiRegionStrategy):
    NAME = "adaptive_multi_region"

    def __init__(self, args):
        super().__init__(args)
        self.region_count = None
        self.spot_history = None
        self.region_spot_availability = None
        self.last_spot_check = None
        self.consecutive_failures = None
        self.region_spot_success = None
        self.last_switch_time = None
        self.region_spot_quality = None
        self.critical_threshold = None
        self.switch_cooldown = None
        self.min_spot_success_rate = None
        self.aggressive_mode = None
        self.conservative_threshold = None

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
        
        # Initialize strategy parameters
        self.region_count = 0  # Will be set in first step
        self.spot_history = {}
        self.region_spot_availability = {}
        self.last_spot_check = {}
        self.consecutive_failures = 0
        self.region_spot_success = {}
        self.last_switch_time = -float('inf')
        self.region_spot_quality = {}
        self.critical_threshold = 0.85  # Use on-demand when time is critical
        self.switch_cooldown = 4  # Minimum steps between region switches
        self.min_spot_success_rate = 0.3  # Minimum success rate to consider spot
        self.aggressive_mode = False
        self.conservative_threshold = 0.7  # Switch to conservative when time is tight
        
        return self

    def _calculate_time_ratio(self) -> float:
        """Calculate how much time we have left relative to work needed."""
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - elapsed
        
        if work_remaining <= 0 or time_remaining <= 0:
            return 0.0
        
        # Account for restart overhead in remaining work
        effective_work = work_remaining + self.restart_overhead
        return time_remaining / effective_work if effective_work > 0 else 0.0

    def _get_best_region_for_spot(self) -> int:
        """Find the region with best historical spot availability."""
        current_region = self.env.get_current_region()
        best_region = current_region
        best_score = -1.0
        
        for region in range(self.env.get_num_regions()):
            if region == current_region:
                continue
                
            success_rate = self.region_spot_success.get(region, 0.5)
            # Prefer regions with higher success rates
            if success_rate > best_score:
                best_score = success_rate
                best_region = region
        
        return best_region

    def _update_spot_history(self, region: int, success: bool):
        """Update historical data for spot availability in a region."""
        if region not in self.region_spot_success:
            self.region_spot_success[region] = 0.5  # Start with neutral prior
            
        # Update success rate with exponential moving average
        alpha = 0.2  # Learning rate
        current = self.region_spot_success[region]
        new_value = 1.0 if success else 0.0
        self.region_spot_success[region] = alpha * new_value + (1 - alpha) * current

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize on first step
        if self.region_count == 0:
            self.region_count = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            for i in range(self.region_count):
                self.region_spot_success[i] = 0.5
        
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - elapsed
        
        # Update spot history for current region
        if last_cluster_type == ClusterType.SPOT:
            # Spot was used in last step, check if it succeeded
            # We consider it a success if we're still in the same cluster type
            # and no restart overhead was incurred
            success = (self.remaining_restart_overhead <= 0)
            self._update_spot_history(current_region, success)
        
        # Calculate critical metrics
        time_ratio = self._calculate_time_ratio()
        
        # Determine if we should switch to aggressive mode
        if time_ratio < self.conservative_threshold:
            self.aggressive_mode = True
        else:
            self.aggressive_mode = False
        
        # If very little time left, use on-demand to guarantee completion
        if time_ratio < 0.3:
            return ClusterType.ON_DEMAND
        
        # If we have plenty of time and spot is available, use it
        if time_ratio > self.critical_threshold and has_spot:
            # But check if current region has good spot history
            region_success = self.region_spot_success.get(current_region, 0.5)
            if region_success >= self.min_spot_success_rate:
                return ClusterType.SPOT
            else:
                # Consider switching to a better region for spot
                if elapsed - self.last_switch_time > self.switch_cooldown * self.env.gap_seconds:
                    best_region = self._get_best_region_for_spot()
                    if best_region != current_region:
                        self.env.switch_region(best_region)
                        self.last_switch_time = elapsed
                        return ClusterType.SPOT
        
        # If spot is available and we're not in critical time, use it
        if has_spot and time_ratio > 0.5:
            # Check if we've had too many consecutive failures
            if self.consecutive_failures < 3:
                return ClusterType.SPOT
        
        # If we're in aggressive mode and spot isn't available, consider switching
        if self.aggressive_mode and not has_spot:
            if elapsed - self.last_switch_time > self.switch_cooldown * self.env.gap_seconds:
                best_region = self._get_best_region_for_spot()
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    self.last_switch_time = elapsed
                    # After switching, use on-demand if in aggressive mode
                    return ClusterType.ON_DEMAND
        
        # Default to on-demand when spot isn't available or time is tight
        if time_ratio < 0.8 or not has_spot:
            # But check if we should pause instead
            if time_ratio > 1.2 and not has_spot:
                # We have time, wait for spot
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        
        # Fallback: pause if we have time and no good options
        return ClusterType.NONE
