import json
from argparse import Namespace
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
        
        # Initialize tracking variables
        self.spot_unavailable_count = 0
        self.last_spot_available = True
        self.switch_count = 0
        self.max_switch_allowed = 3
        self.best_region = 0
        self.region_spot_history = {}
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Calculate remaining work and time
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # Calculate minimum time needed with overhead
        overhead_penalty = self.restart_overhead if self.remaining_restart_overhead > 0 else 0
        min_time_needed = remaining_work + overhead_penalty
        
        # If we're critically behind schedule, use on-demand
        if remaining_time < min_time_needed * 1.2:
            return ClusterType.ON_DEMAND
        
        # If we're ahead of schedule, be conservative
        if remaining_time > remaining_work * 2.5:
            # We can afford to be more aggressive with spot
            if has_spot:
                # Try to find better region
                if not self.last_spot_available and self.switch_count < self.max_switch_allowed:
                    next_region = (current_region + 1) % num_regions
                    self.env.switch_region(next_region)
                    self.switch_count += 1
                    return ClusterType.NONE
                self.last_spot_available = True
                self.spot_unavailable_count = 0
                return ClusterType.SPOT
            else:
                # Spot unavailable in current region
                self.last_spot_available = False
                self.spot_unavailable_count += 1
                
                # If spot has been unavailable for too long in this region, try another
                if self.spot_unavailable_count >= 2 and self.switch_count < self.max_switch_allowed:
                    next_region = (current_region + 1) % num_regions
                    self.env.switch_region(next_region)
                    self.switch_count += 1
                    self.spot_unavailable_count = 0
                    return ClusterType.NONE
                
                # Use on-demand if we can't switch or spot is consistently unavailable
                if remaining_time < min_time_needed * 1.5 or self.switch_count >= self.max_switch_allowed:
                    return ClusterType.ON_DEMAND
                
                # Wait and try spot again next time
                return ClusterType.NONE
        else:
            # Moderate time pressure - balanced strategy
            if has_spot:
                self.last_spot_available = True
                self.spot_unavailable_count = 0
                return ClusterType.SPOT
            else:
                self.last_spot_available = False
                self.spot_unavailable_count += 1
                
                # Try one region switch if we haven't switched too much
                if self.spot_unavailable_count >= 2 and self.switch_count < self.max_switch_allowed:
                    next_region = (current_region + 1) % num_regions
                    self.env.switch_region(next_region)
                    self.switch_count += 1
                    self.spot_unavailable_count = 0
                    return ClusterType.NONE
                
                # Use on-demand to ensure progress
                return ClusterType.ON_DEMAND