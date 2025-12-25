import sys
import os
import argparse
import math
from typing import List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

@dataclass
class State:
    progress: float
    time: float
    current_type: ClusterType
    restart_remaining: float
    
class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__()
        self.spot_price = 0.97
        self.on_demand_price = 3.06
        self.safety_margin = 0.2
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        time_step = self.env.gap_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        total_work = self.task_duration
        
        # Calculate current progress
        completed_work = sum(self.task_done_time) if self.task_done_time else 0
        remaining_work = max(0.0, total_work - completed_work)
        time_remaining = deadline - elapsed
        
        # If already finished or past deadline
        if remaining_work <= 0 or time_remaining <= 0:
            return ClusterType.NONE
        
        # Calculate progress rates
        spot_rate = 1.0  # work per second when running on spot
        on_demand_rate = 1.0  # work per second when running on demand
        none_rate = 0.0  # work per second when paused
        
        # Calculate effective rates considering restart overhead
        # For spot: we need to account for potential interruptions
        # For on-demand: no interruptions, just the work rate
        
        # Estimate remaining time needed for each strategy
        time_needed_on_demand = remaining_work / on_demand_rate
        time_needed_spot = remaining_work / spot_rate
        
        # Calculate minimum time needed if we start on-demand now
        min_time_needed = time_needed_on_demand
        
        # Calculate slack time
        slack_time = time_remaining - min_time_needed
        
        # Determine current state
        current_type = last_cluster_type
        
        # Decision logic
        if time_remaining <= min_time_needed * (1 + self.safety_margin):
            # Running out of time, use on-demand
            if last_cluster_type != ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        elif has_spot:
            # Spot is available
            if last_cluster_type == ClusterType.SPOT:
                # Already on spot, continue
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.ON_DEMAND:
                # On on-demand, consider switching to spot if we have enough slack
                # Only switch if we have significant slack to absorb potential restart overhead
                if slack_time > restart_overhead * 2:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:  # NONE or other
                return ClusterType.SPOT
        else:
            # Spot not available
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            elif last_cluster_type == ClusterType.SPOT:
                # Spot was preempted, switch to on-demand if needed
                # Check if we have time to wait for spot to return
                estimated_wait_time = 3600  # 1 hour estimate for spot to return
                if time_remaining > time_needed_on_demand + estimated_wait_time:
                    # Can afford to wait
                    return ClusterType.NONE
                else:
                    # Need to switch to on-demand
                    return ClusterType.ON_DEMAND
            else:  # NONE
                # We're waiting, check if we should continue waiting or switch to on-demand
                wait_time_so_far = time_step  # Approximate
                max_wait_time = min(restart_overhead * 3, time_remaining - time_needed_on_demand)
                
                if wait_time_so_far < max_wait_time and slack_time > restart_overhead:
                    # Continue waiting for spot
                    return ClusterType.NONE
                else:
                    # Switch to on-demand
                    return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)