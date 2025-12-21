import json
from argparse import Namespace
import math
from typing import List, Tuple
from collections import deque

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
        
        # Initialize strategy state
        self.region_history = []
        self.spot_availability_history = []
        self.current_plan = []
        self.plan_index = 0
        self.consecutive_failures = 0
        self.last_switch_time = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Get current state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - elapsed
        gap = self.env.gap_seconds
        
        # Calculate effective work needed considering potential overhead
        effective_work_needed = work_remaining
        if last_cluster_type != ClusterType.NONE:
            # If currently running, account for potential restart
            effective_work_needed += self.restart_overhead
        
        # Calculate minimum time needed with on-demand
        min_time_needed = effective_work_needed
        
        # Emergency mode: if we're running out of time, use on-demand
        safety_margin = 2 * self.restart_overhead
        if time_remaining < min_time_needed + safety_margin:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                # Switch to on-demand
                return ClusterType.ON_DEMAND
        
        # Calculate optimal region strategy
        # Prefer regions where spot is currently available
        if has_spot:
            # Calculate risk-adjusted value
            time_per_step = gap
            if last_cluster_type == ClusterType.SPOT:
                # Continuing spot - no overhead
                return ClusterType.SPOT
            else:
                # Switching to spot - calculate if worth it
                spot_steps_needed = math.ceil(work_remaining / gap)
                od_steps_needed = math.ceil(effective_work_needed / gap)
                
                # Account for potential spot failures
                failure_prob = min(0.3, self.consecutive_failures * 0.1)
                expected_spot_steps = spot_steps_needed / (1 - failure_prob)
                
                spot_time = expected_spot_steps * gap
                od_time = od_steps_needed * gap
                
                if spot_time < od_time and time_remaining - spot_time > safety_margin:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND if last_cluster_type != ClusterType.NONE else ClusterType.NONE
        else:
            # No spot available in current region
            # Try to find a region with spot
            best_region = current_region
            found_spot_region = False
            
            # Simple round-robin search for spot availability
            for i in range(1, num_regions):
                test_region = (current_region + i) % num_regions
                # We don't have access to other regions' spot status in current timestep
                # So we'll switch optimistically
                if test_region != current_region:
                    self.env.switch_region(test_region)
                    # After switching, we need to check spot in next timestep
                    return ClusterType.NONE
            
            # If no region switch was made and no spot available, use on-demand if needed
            if work_remaining > 0 and time_remaining < work_remaining + 3 * gap:
                return ClusterType.ON_DEMAND
            else:
                # Wait for spot to become available
                return ClusterType.NONE
    
    def _estimate_completion_time(self, use_spot: bool, current_region: int) -> float:
        """Estimate completion time for a given strategy."""
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if not use_spot:
            # On-demand completion
            if self.env.cluster_type == ClusterType.ON_DEMAND:
                return work_remaining
            else:
                return work_remaining + self.restart_overhead
        else:
            # Spot completion with estimated failures
            avg_spot_uptime = 4 * self.env.gap_seconds  # Assume 4-hour average spot uptime
            expected_failures = work_remaining / avg_spot_uptime
            overhead_time = expected_failures * self.restart_overhead
            return work_remaining + overhead_time
