import json
from argparse import Namespace
from enum import Enum
from typing import List
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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
        
        # Initialize state variables
        self.steps_without_spot = 0
        self.current_region = 0
        self.region_attempts = {}
        self.last_decision = ClusterType.NONE
        self.consecutive_failures = 0
        self.spot_attempts = 0
        self.max_spot_attempts = 3
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # If no work left, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # Calculate time needed for on-demand completion
        time_needed_ondemand = remaining_work + self.restart_overhead
        
        # Emergency mode: if we're running out of time, use on-demand
        if remaining_time < time_needed_ondemand * 1.2:
            return ClusterType.ON_DEMAND
            
        # Calculate how many spot attempts we can afford
        max_affordable_failures = max(0, int((remaining_time - time_needed_ondemand) / self.restart_overhead))
        
        # Try spot if available and we can afford failures
        if has_spot and max_affordable_failures > 0:
            self.steps_without_spot = 0
            self.spot_attempts += 1
            
            # After too many spot attempts, try on-demand for reliability
            if self.spot_attempts > self.max_spot_attempts:
                self.spot_attempts = 0
                return ClusterType.ON_DEMAND
                
            return ClusterType.SPOT
            
        # Spot not available
        self.steps_without_spot += 1
        
        # If spot unavailable for too long, consider switching region
        if self.steps_without_spot > 2:
            num_regions = self.env.get_num_regions()
            
            # Try to find a better region
            best_region = None
            current_idx = self.env.get_current_region()
            
            # Simple round-robin region switching
            next_region = (current_idx + 1) % num_regions
            self.env.switch_region(next_region)
            self.steps_without_spot = 0
            
            # After switching, wait one step to assess new region
            return ClusterType.NONE
            
        # If we can't use spot and don't need to switch, use on-demand
        # but only if we're making progress
        if remaining_work > 0 and remaining_time > time_needed_ondemand:
            return ClusterType.ON_DEMAND
            
        # Otherwise, wait
        return ClusterType.NONE