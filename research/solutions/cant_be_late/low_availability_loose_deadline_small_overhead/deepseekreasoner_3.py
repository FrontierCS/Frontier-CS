import argparse
from enum import Enum
from typing import List, Optional
import math

class ClusterType(Enum):
    SPOT = "spot"
    ON_DEMAND = "on_demand"
    NONE = "none"

class Strategy:
    def __init__(self, args):
        self.args = args
        self.env = None
        self.task_duration = None
        self.task_done_time = None
        self.deadline = None
        self.restart_overhead = None

class Solution(Strategy):
    NAME = "adaptive_threshold"
    
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE
            
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        gap = self.env.gap_seconds
        
        if time_left <= 0:
            return ClusterType.ON_DEMAND
            
        work_needed = remaining_work
        time_needed_no_overhead = work_needed
        min_time_needed = work_needed + self.restart_overhead
        
        if min_time_needed > time_left:
            return ClusterType.ON_DEMAND
        
        current_type = self.env.cluster_type
        is_running = current_type in [ClusterType.SPOT, ClusterType.ON_DEMAND]
        
        if not is_running:
            overhead_time = self.restart_overhead
        else:
            overhead_time = 0
        
        effective_time_left = time_left - overhead_time
        required_rate = work_needed / effective_time_left if effective_time_left > 0 else float('inf')
        
        spot_cost = 0.97
        ondemand_cost = 3.06
        spot_saving = ondemand_cost - spot_cost
        
        if required_rate > 1.0:
            return ClusterType.ON_DEMAND
        
        risk_factor = 0.7
        if has_spot and required_rate < risk_factor:
            return ClusterType.SPOT
        
        if not has_spot:
            if required_rate > 0.8:
                return ClusterType.ON_DEMAND
            buffer_needed = work_needed + self.restart_overhead
            if time_left < buffer_needed * 1.2:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        if required_rate > 0.9:
            return ClusterType.ON_DEMAND
        
        return ClusterType.SPOT
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)