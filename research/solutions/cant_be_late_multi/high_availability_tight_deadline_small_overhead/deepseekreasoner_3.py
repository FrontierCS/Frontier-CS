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
        
        # Precompute cost parameters
        self.spot_hourly = 0.9701
        self.ondemand_hourly = 3.06
        self.gap_hours = self.env.gap_seconds / 3600.0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get current progress and time
        elapsed_hours = self.env.elapsed_seconds / 3600.0
        work_done = sum(self.task_done_time) / 3600.0
        work_remaining = self.task_duration / 3600.0 - work_done
        deadline_hours = self.deadline / 3600.0
        overhead_hours = self.restart_overhead / 3600.0
        
        # If work is done, return NONE
        if work_remaining <= 0:
            return ClusterType.NONE
            
        # Calculate absolute latest time we must start on-demand
        # Account for possible restart overhead if switching to on-demand
        if last_cluster_type == ClusterType.ON_DEMAND:
            required_hours = work_remaining
        else:
            required_hours = work_remaining + overhead_hours
            
        time_remaining = deadline_hours - elapsed_hours
        
        # Emergency mode: must use on-demand to meet deadline
        if time_remaining <= required_hours + self.gap_hours:
            return ClusterType.ON_DEMAND
        
        # Calculate remaining slack
        slack = time_remaining - required_hours
        
        # Aggressive spot strategy when we have plenty of slack
        if slack > overhead_hours * 3:
            # Try to find a region with spot availability
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            
            # If current region doesn't have spot, try others
            if not has_spot:
                for i in range(1, num_regions):
                    next_region = (current_region + i) % num_regions
                    self.env.switch_region(next_region)
                    # Note: has_spot parameter is for previous region
                    # We'll discover new region's availability next step
                    break
            
            # Use spot if available, otherwise wait
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            # Conservative mode: use on-demand when slack is limited
            return ClusterType.ON_DEMAND