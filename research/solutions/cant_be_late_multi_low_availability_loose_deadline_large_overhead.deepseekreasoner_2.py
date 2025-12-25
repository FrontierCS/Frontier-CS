import json
from argparse import Namespace
from typing import List, Tuple
import heapq
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
        
        # Initialize strategy state
        self.total_work_needed = self.task_duration
        self.spot_price = 0.9701  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.spot_to_ondemand_ratio = self.spot_price / self.ondemand_price
        
        # Precomputed decision thresholds
        self.switch_penalty = self.restart_overhead  # seconds
        self.time_step = 3600.0  # 1 hour in seconds
        
        # Safety margins
        self.safety_factor = 1.2
        self.critical_time_threshold = self.switch_penalty * 4
        
        return self

    def _get_progress(self) -> float:
        """Get current progress percentage."""
        work_done = sum(self.task_done_time)
        return work_done / self.total_work_needed

    def _get_remaining_time(self) -> float:
        """Get remaining time until deadline."""
        return self.deadline - self.env.elapsed_seconds

    def _get_work_remaining(self) -> float:
        """Get remaining work needed."""
        work_done = sum(self.task_done_time)
        return self.total_work_needed - work_done

    def _should_use_ondemand(self, last_cluster_type: ClusterType, 
                            has_spot: bool) -> bool:
        """Determine if we should switch to on-demand."""
        remaining_time = self._get_remaining_time()
        work_remaining = self._get_work_remaining()
        
        # If no time left, must use on-demand
        if remaining_time <= 0:
            return True
            
        # Calculate minimum time needed with on-demand
        min_time_needed = work_remaining
        if last_cluster_type != ClusterType.ON_DEMAND:
            min_time_needed += self.switch_penalty
            
        # Add safety margin
        min_time_needed *= self.safety_factor
        
        # Critical condition: if we can't finish even with on-demand
        if remaining_time <= self.critical_time_threshold:
            return True
            
        # If we need to guarantee progress
        if remaining_time <= min_time_needed:
            return True
            
        # If spot is unavailable and we have limited time
        if not has_spot and remaining_time < work_remaining * 2:
            return True
            
        return False

    def _find_best_region(self, current_region: int, 
                         last_cluster_type: ClusterType) -> Tuple[int, bool]:
        """Find the best region to switch to considering spot availability."""
        num_regions = self.env.get_num_regions()
        best_region = current_region
        should_switch = False
        
        # If we're in critical time, stay put to avoid switch penalty
        remaining_time = self._get_remaining_time()
        if remaining_time < self.switch_penalty * 3:
            return current_region, False
            
        # Try to predict if switching might help
        # For now, implement a simple round-robin strategy when stuck
        if last_cluster_type == ClusterType.NONE:
            # When idle, try the next region
            next_region = (current_region + 1) % num_regions
            return next_region, True
            
        return best_region, should_switch

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get current state
        current_region = self.env.get_current_region()
        remaining_time = self._get_remaining_time()
        work_remaining = self._get_work_remaining()
        
        # If no time left, fail fast
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND
            
        # If work is done, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE
            
        # Calculate efficiency metrics
        time_per_work_unit = self.time_step
        if self.remaining_restart_overhead > 0:
            time_per_work_unit = self.time_step - self.remaining_restart_overhead
            
        # Check if we should use on-demand
        if self._should_use_ondemand(last_cluster_type, has_spot):
            # If we're already on-demand, stay
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            # Otherwise switch to on-demand
            return ClusterType.ON_DEMAND
        
        # Try to use spot if available
        if has_spot:
            # Only switch regions if we're not making progress
            if last_cluster_type == ClusterType.NONE:
                best_region, should_switch = self._find_best_region(
                    current_region, last_cluster_type
                )
                if should_switch and best_region != current_region:
                    self.env.switch_region(best_region)
            return ClusterType.SPOT
        
        # Spot not available - check if we should wait or use on-demand
        time_needed_with_wait = work_remaining + self.switch_penalty
        time_needed_with_ondemand = work_remaining
        
        if last_cluster_type != ClusterType.ON_DEMAND:
            time_needed_with_ondemand += self.switch_penalty
            
        # If waiting for spot might cause us to miss deadline
        if remaining_time < time_needed_with_wait * 1.5:
            return ClusterType.ON_DEMAND
            
        # Otherwise wait (use NONE) and hope spot becomes available
        # But only if we have enough time buffer
        if remaining_time > work_remaining * 3:
            return ClusterType.NONE
            
        # Default to on-demand if uncertain
        return ClusterType.ON_DEMAND
