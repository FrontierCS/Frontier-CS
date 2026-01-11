import json
import math
from argparse import Namespace
from enum import Enum
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        
        # Initialize strategy state
        self.region_history = []
        self.spot_history = []
        self.switch_count = 0
        self.consecutive_on_demand = 0
        self.last_region = -1
        self.consecutive_no_spot = 0
        self.fallback_threshold = 4
        
        # Precompute some values for efficiency
        self.task_duration_sec = self.task_duration
        self.deadline_sec = self.deadline
        self.overhead_sec = self.restart_overhead
        self.gap_sec = self.env.gap_seconds if hasattr(self.env, 'gap_seconds') else 3600.0
        
        # Cost parameters (from problem description)
        self.spot_cost_per_sec = 0.9701 / 3600.0
        self.ondemand_cost_per_sec = 3.06 / 3600.0
        
        # Time thresholds
        self.emergency_time = self.overhead_sec * 3
        self.critical_time = self.overhead_sec * 6
        
        return self

    def _get_remaining_work(self) -> float:
        """Get remaining work in seconds."""
        return self.task_duration_sec - sum(self.task_done_time)

    def _get_remaining_time(self) -> float:
        """Get remaining time until deadline in seconds."""
        return self.deadline_sec - self.env.elapsed_seconds

    def _get_work_progress_rate(self) -> float:
        """Calculate effective work progress rate considering overheads."""
        total_work = sum(self.task_done_time)
        if total_work == 0:
            return 0.0
        effective_time = self.env.elapsed_seconds
        return total_work / effective_time if effective_time > 0 else 0.0

    def _should_switch_region(self, current_region: int, has_spot: bool) -> bool:
        """Determine if we should switch regions."""
        if self.env.get_num_regions() <= 1:
            return False
            
        remaining_work = self._get_remaining_work()
        remaining_time = self._get_remaining_time()
        
        # If we're in emergency mode, don't switch
        if remaining_time < remaining_work + self.emergency_time:
            return False
            
        # If no spot in current region and we have time to switch
        if not has_spot and self.consecutive_no_spot > 2:
            # Only switch if we're not making progress
            if self.consecutive_no_spot > self.fallback_threshold:
                return True
                
        # If we've been in one region too long without spot, try another
        if self.consecutive_no_spot > 8:
            return True
            
        return False

    def _select_best_region(self, current_region: int) -> int:
        """Select the best region to switch to."""
        num_regions = self.env.get_num_regions()
        if num_regions <= 1:
            return current_region
            
        # Simple round-robin selection
        next_region = (current_region + 1) % num_regions
        return next_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        remaining_work = self._get_remaining_work()
        remaining_time = self._get_remaining_time()
        
        # Update history
        if current_region != self.last_region:
            self.switch_count += 1
            self.consecutive_no_spot = 0
        self.last_region = current_region
        
        # If no work left, pause
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If no time left, use on-demand as last resort
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND
            
        # Calculate time pressure
        required_rate = remaining_work / max(remaining_time, 0.1)
        current_rate = self._get_work_progress_rate()
        
        # Emergency situation: must use on-demand to finish
        if remaining_time < remaining_work + self.emergency_time:
            self.consecutive_on_demand += 1
            return ClusterType.ON_DEMAND
            
        # Critical situation: be conservative
        if remaining_time < remaining_work + self.critical_time:
            if has_spot and required_rate < 0.8:  # We have some slack
                self.consecutive_on_demand = 0
                return ClusterType.SPOT
            else:
                self.consecutive_on_demand += 1
                return ClusterType.ON_DEMAND
        
        # Check if we should switch regions
        if self._should_switch_region(current_region, has_spot):
            best_region = self._select_best_region(current_region)
            if best_region != current_region:
                self.env.switch_region(best_region)
                # After switching, we need to handle overhead
                # Return NONE for this step to account for switch overhead
                return ClusterType.NONE
        
        # Normal operation: prefer spot when available
        if has_spot:
            # If we've been using on-demand for too long, try spot
            if self.consecutive_on_demand > 3:
                self.consecutive_on_demand = 0
                self.consecutive_no_spot = 0
                return ClusterType.SPOT
                
            # Use spot if we have reasonable time buffer
            time_buffer = remaining_time - remaining_work
            if time_buffer > self.overhead_sec * 2:
                self.consecutive_on_demand = 0
                self.consecutive_no_spot = 0
                return ClusterType.SPOT
            else:
                # Limited buffer, use on-demand
                self.consecutive_on_demand += 1
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            self.consecutive_no_spot += 1
            self.consecutive_on_demand += 1
            
            # If we haven't had spot for a while, consider pausing
            if self.consecutive_no_spot > 5 and remaining_time > remaining_work + self.overhead_sec * 4:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND