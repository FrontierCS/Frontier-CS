import json
from argparse import Namespace
import math
from typing import List, Dict

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
        
        # Initialize strategy parameters
        self.time_step = self.env.gap_seconds
        self.total_work_needed = self.task_duration
        self.overhead_seconds = self.restart_overhead
        self.deadline_seconds = self.deadline
        
        # Prices (from problem statement)
        self.spot_price = 0.9701  # $/hr
        self.ondemand_price = 3.06  # $/hr
        
        # State tracking
        self.last_decision = None
        self.region_history = []
        self.spot_availability_history = []
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Track state
        self.spot_availability_history.append(has_spot)
        current_region = self.env.get_current_region()
        self.region_history.append(current_region)
        
        # Calculate current progress
        completed_work = sum(self.task_done_time) if self.task_done_time else 0
        remaining_work = self.total_work_needed - completed_work
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline_seconds - elapsed
        
        # If task is already completed, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If deadline missed or impossible to finish, use on-demand to minimize penalty
        if remaining_time <= 0 or remaining_work > remaining_time:
            return ClusterType.ON_DEMAND
            
        # Calculate conservative completion estimates
        time_per_work_unit = self.time_step
        if self.remaining_restart_overhead > 0:
            time_per_work_unit = self.time_step  # Overhead already accounted for
        
        # Estimate minimum time needed with perfect conditions
        min_time_needed = remaining_work
        if self.remaining_restart_overhead > 0:
            min_time_needed += self.remaining_restart_overhead
            
        # Calculate urgency factor (how tight is the deadline)
        urgency = max(0.0, min_time_needed / max(remaining_time, 0.1))
        
        # If we're in overhead period, we can't do work anyway
        if self.remaining_restart_overhead > self.time_step * 0.9:
            # During significant overhead, consider switching to better region
            if has_spot and urgency < 0.8:
                return ClusterType.NONE
            else:
                # Try to find a region with spot availability
                num_regions = self.env.get_num_regions()
                for i in range(num_regions):
                    if i != current_region:
                        self.env.switch_region(i)
                        return ClusterType.NONE
                return ClusterType.NONE
        
        # Strategy decision logic
        if has_spot:
            # Use spot when available and we have time buffer
            if urgency < 0.85:  # We have some buffer
                return ClusterType.SPOT
            else:
                # Getting close to deadline, use on-demand to ensure completion
                return ClusterType.ON_DEMAND
        else:
            # No spot available in current region
            if urgency > 0.7:
                # Urgent: use on-demand immediately
                return ClusterType.ON_DEMAND
            else:
                # Try to find a region with spot
                num_regions = self.env.get_num_regions()
                
                # Simple round-robin search for spot
                next_region = (current_region + 1) % num_regions
                if next_region != current_region:
                    self.env.switch_region(next_region)
                    # After switching, check if we should use spot in new region
                    # but we don't know availability yet, so wait one step
                    return ClusterType.NONE
                else:
                    # Only one region or already tried all
                    if urgency > 0.3:
                        return ClusterType.ON_DEMAND
                    else:
                        return ClusterType.NONE
