import json
from argparse import Namespace
from enum import Enum
from typing import List, Tuple, Optional
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Action(Enum):
    SPOT = "spot"
    ON_DEMAND = "on_demand"
    NONE = "none"
    SWITCH_SPOT = "switch_spot"
    SWITCH_ON_DEMAND = "switch_ondemand"


class State:
    def __init__(self, region: int, cluster_type: ClusterType, work_done: float, overhead_remaining: float):
        self.region = region
        self.cluster_type = cluster_type
        self.work_done = work_done
        self.overhead_remaining = overhead_remaining
    
    def __hash__(self):
        return hash((self.region, self.cluster_type, round(self.work_done, 6), round(self.overhead_remaining, 6)))
    
    def __eq__(self, other):
        return (self.region == other.region and 
                self.cluster_type == other.cluster_type and
                abs(self.work_done - other.work_done) < 1e-6 and
                abs(self.overhead_remaining - other.overhead_remaining) < 1e-6)
    
    def __lt__(self, other):
        return self.work_done < other.work_done


class Solution(MultiRegionStrategy):
    NAME = "optimized_multi_region"
    
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
        
        # Precompute constants
        self.gap_seconds = 3600.0  # 1 hour per timestep
        self.spot_price = 0.9701
        self.on_demand_price = 3.06
        self.spot_available_cache = {}
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get current state
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - elapsed
        
        # If no work left, return NONE
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # If we can't finish even with continuous on-demand, use on-demand
        min_time_needed = work_remaining + self.restart_overhead
        if time_remaining <= min_time_needed:
            # Check if we need to switch to on-demand
            if last_cluster_type != ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND if work_remaining > 0 else ClusterType.NONE
        
        # If we have pending overhead, wait it out
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Calculate slack ratio
        slack_ratio = time_remaining / work_remaining if work_remaining > 0 else float('inf')
        
        # If we have plenty of slack and spot is available, use spot
        if has_spot and slack_ratio > 1.3:
            # Only use spot if we're not too close to deadline
            safety_margin = self.restart_overhead * 3
            if time_remaining - work_remaining > safety_margin:
                return ClusterType.SPOT
        
        # If spot is available and we have moderate slack, use spot
        if has_spot and slack_ratio > 1.1:
            # Check if we've been preempted recently
            recent_preemptions = 0
            if len(self.task_done_time) >= 2:
                # Count timesteps with less than full work
                for work in self.task_done_time[-min(5, len(self.task_done_time)):]:
                    if work < self.gap_seconds * 0.9:
                        recent_preemptions += 1
            
            if recent_preemptions < 2:  # Not too many recent preemptions
                return ClusterType.SPOT
        
        # Otherwise use on-demand
        return ClusterType.ON_DEMAND