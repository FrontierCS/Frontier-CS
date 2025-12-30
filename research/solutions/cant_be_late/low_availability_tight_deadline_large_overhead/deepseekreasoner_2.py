import argparse
import math
from enum import Enum
from typing import List, Tuple

class ClusterType(Enum):
    SPOT = "SPOT"
    ON_DEMAND = "ON_DEMAND"
    NONE = "NONE"

class Strategy:
    def __init__(self, args):
        self.env = None
        self.task_duration = None
        self.task_done_time = None
        self.deadline = None
        self.restart_overhead = None
    
    def solve(self, spec_path: str) -> "Strategy":
        return self

class Solution(Strategy):
    NAME = "adaptive_conservative"
    
    def __init__(self, args):
        super().__init__(args)
        self.use_on_demand = False
        self.last_spot_availability = True
        self.consecutive_unavailable = 0
        self.work_done = 0.0
        self.time_elapsed = 0.0
        self.safety_margin = 0.5 * 3600  # 30 minutes in seconds
        self.min_spot_percentage = 0.2
    
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state
        self.time_elapsed = self.env.elapsed_seconds
        self.last_spot_availability = has_spot
        
        # Calculate remaining work
        if self.task_done_time:
            self.work_done = sum(end - start for start, end in self.task_done_time)
        remaining_work = self.task_duration - self.work_done
        
        # Calculate time remaining until deadline
        time_remaining = self.deadline - self.time_elapsed
        
        # Track spot availability pattern
        if not has_spot:
            self.consecutive_unavailable += 1
        else:
            self.consecutive_unavailable = 0
        
        # If we're very close to deadline or out of time, use on-demand
        if time_remaining <= self.restart_overhead + self.safety_margin:
            return ClusterType.ON_DEMAND
        
        # If remaining work can be done within time_remaining with on-demand
        # (accounting for restart overhead if switching from none)
        if last_cluster_type == ClusterType.NONE:
            effective_time = time_remaining - self.restart_overhead
        else:
            effective_time = time_remaining
        
        # Calculate required work rate
        required_rate = remaining_work / effective_time if effective_time > 0 else float('inf')
        
        # If we need to work faster than spot can provide (accounting for availability),
        # switch to on-demand
        if required_rate > 0.8:  # 80% utilization threshold
            self.use_on_demand = True
        
        # If spot is consistently unavailable, switch to on-demand
        if self.consecutive_unavailable > 10:  # 10 consecutive unavailable steps
            self.use_on_demand = True
        
        # If we've decided to use on-demand, stick with it
        if self.use_on_demand:
            return ClusterType.ON_DEMAND
        
        # Use spot if available and we have enough time buffer
        if has_spot:
            # Calculate if we have enough time for spot with potential restarts
            # Use a conservative estimate: assume worst-case spot availability
            conservative_time_needed = remaining_work + 2 * self.restart_overhead
            
            if time_remaining > conservative_time_needed:
                return ClusterType.SPOT
            else:
                # Not enough buffer, use on-demand
                self.use_on_demand = True
                return ClusterType.ON_DEMAND
        else:
            # Spot not available, wait if we have time buffer
            if time_remaining > remaining_work + self.safety_margin:
                return ClusterType.NONE
            else:
                # Need to make progress, use on-demand
                self.use_on_demand = True
                return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)