import json
from argparse import Namespace
import math
from typing import List, Tuple

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
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.spot_price / self.ondemand_price
        
        # Region tracking
        self.region_history = []
        self.current_region_streak = 0
        self.last_action = ClusterType.NONE
        self.consecutive_failures = 0
        self.switch_count = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task is complete, do nothing
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 1e-9:
            return ClusterType.NONE
            
        # Calculate time constraints
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        time_per_step = self.env.gap_seconds
        
        # Calculate effective work rates
        effective_spot_rate = time_per_step / (time_per_step + self.restart_overhead)
        required_steps_spot = math.ceil(remaining_work / (time_per_step * effective_spot_rate))
        required_steps_ondemand = math.ceil(remaining_work / time_per_step)
        
        # Calculate minimum steps needed
        min_time_spot = required_steps_spot * time_per_step
        min_time_ondemand = required_steps_ondemand * time_per_step
        
        # Safety margin (15% of remaining time)
        safety_margin = 0.15 * remaining_time
        
        # Decision logic
        if remaining_time < min_time_ondemand + safety_margin:
            # Critical: must use on-demand to finish on time
            if self.remaining_restart_overhead <= 0:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
                
        elif remaining_time < min_time_spot + safety_margin:
            # Moderate: can use spot but be ready to switch to on-demand
            if has_spot and self.consecutive_failures < 2:
                return ClusterType.SPOT
            elif self.remaining_restart_overhead <= 0:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
                
        else:
            # Plenty of time: optimize for cost
            if has_spot:
                # Use spot if available
                if self.consecutive_failures >= 2:
                    # Too many failures, try another region
                    if self.current_region_streak > 3:
                        current = self.env.get_current_region()
                        next_region = (current + 1) % self.env.get_num_regions()
                        self.env.switch_region(next_region)
                        self.current_region_streak = 0
                        self.consecutive_failures = 0
                        self.switch_count += 1
                self.current_region_streak += 1
                self.consecutive_failures = 0
                return ClusterType.SPOT
            else:
                # Spot not available
                self.consecutive_failures += 1
                
                # Consider region switch if spot keeps failing
                if self.consecutive_failures > 3 and self.current_region_streak > 2:
                    current = self.env.get_current_region()
                    next_region = (current + 1) % self.env.get_num_regions()
                    self.env.switch_region(next_region)
                    self.current_region_streak = 0
                    self.consecutive_failures = 0
                    self.switch_count += 1
                    return ClusterType.NONE
                    
                # If we have pending overhead, wait
                if self.remaining_restart_overhead > 0:
                    return ClusterType.NONE
                    
                # Small chance to use on-demand if we're making good progress
                progress_ratio = sum(self.task_done_time) / self.task_duration
                if progress_ratio > 0.7 and remaining_time > min_time_ondemand * 1.5:
                    return ClusterType.ON_DEMAND
                    
                return ClusterType.NONE