import json
from argparse import Namespace
from typing import List
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "adaptive_spot_strategy"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regions = 0
        self.region_spot_history = []
        self.spot_availability_window = 3
        self.critical_time_threshold = 0.3
        self.min_spot_confidence = 0.7
        self.last_action = ClusterType.NONE
        self.consecutive_spot_failures = 0
        self.max_spot_failures = 2

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
        
        self.regions = len(config["trace_files"])
        self.region_spot_history = [[] for _ in range(self.regions)]
        
        return self

    def _get_work_done(self) -> float:
        """Calculate total work done so far."""
        return sum(self.task_done_time)

    def _get_time_remaining(self) -> float:
        """Calculate time remaining until deadline."""
        return self.deadline - self.env.elapsed_seconds

    def _get_work_remaining(self) -> float:
        """Calculate work remaining."""
        return self.task_duration - self._get_work_done()

    def _is_critical_time(self) -> bool:
        """
        Check if we're in critical time where we need to 
        switch to on-demand to meet deadline.
        """
        work_remaining = self._get_work_remaining()
        time_remaining = self._get_time_remaining()
        
        if time_remaining <= 0:
            return True
            
        # Calculate time needed with overhead if we switch now
        min_time_needed = work_remaining
        if self.last_action != ClusterType.ON_DEMAND:
            min_time_needed += self.restart_overhead
            
        # Add safety margin
        min_time_needed *= (1 + self.critical_time_threshold)
        
        return time_remaining <= min_time_needed

    def _get_best_region(self, current_region: int, has_spot: bool) -> int:
        """
        Find the best region to run in based on spot availability history.
        """
        if self.regions <= 1:
            return current_region
            
        best_region = current_region
        best_score = -1
        
        # If current region has spot and we have few failures, stay
        if has_spot and self.consecutive_spot_failures < self.max_spot_failures:
            current_history = self.region_spot_history[current_region]
            if len(current_history) >= self.spot_availability_window:
                spot_ratio = sum(current_history[-self.spot_availability_window:]) / self.spot_availability_window
                if spot_ratio >= self.min_spot_confidence:
                    return current_region
        
        # Evaluate other regions
        for region in range(self.regions):
            if region == current_region:
                continue
                
            history = self.region_spot_history[region]
            if len(history) < self.spot_availability_window:
                continue
                
            # Calculate spot availability in recent window
            recent_history = history[-self.spot_availability_window:]
            spot_ratio = sum(recent_history) / len(recent_history)
            
            # Prefer regions with higher spot availability
            if spot_ratio > best_score:
                best_score = spot_ratio
                best_region = region
                
        return best_region

    def _update_spot_history(self, region: int, has_spot: bool):
        """Update spot availability history for a region."""
        if region < len(self.region_spot_history):
            self.region_spot_history[region].append(1 if has_spot else 0)
            # Keep history limited to avoid memory issues
            if len(self.region_spot_history[region]) > 100:
                self.region_spot_history[region] = self.region_spot_history[region][-100:]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        
        # Update spot history for current region
        self._update_spot_history(current_region, has_spot)
        
        # Reset spot failure counter if we succeeded
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.consecutive_spot_failures = 0
        elif last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        
        # Check if we're in critical time
        if self._is_critical_time():
            # In critical time, use on-demand to ensure meeting deadline
            best_action = ClusterType.ON_DEMAND
            
            # Switch region only if current one doesn't have good history
            if not has_spot or self.consecutive_spot_failures >= self.max_spot_failures:
                best_region = self._get_best_region(current_region, has_spot)
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    self.consecutive_spot_failures = 0
        else:
            # Not in critical time, try to use spot to save cost
            
            # Find best region for spot
            best_region = self._get_best_region(current_region, has_spot)
            
            # Switch region if beneficial
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.consecutive_spot_failures = 0
                # After switching, we need to check spot availability in new region
                # Since we don't know yet, be conservative
                best_action = ClusterType.NONE
            else:
                # Stay in current region
                if has_spot and self.consecutive_spot_failures < self.max_spot_failures:
                    best_action = ClusterType.SPOT
                else:
                    # No spot available or too many failures, pause
                    best_action = ClusterType.NONE
        
        self.last_action = best_action
        return best_action