import argparse
from enum import Enum
from typing import List, Tuple
import math

class ClusterType(Enum):
    SPOT = "SPOT"
    ON_DEMAND = "ON_DEMAND"
    NONE = "NONE"

class Strategy:
    pass

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.overhead_remaining = 0
        self.spot_unavailable_streak = 0
        self.aggressiveness = 0.7
        self.min_safety_margin = 0.5
        self.consecutive_spot_failures = 0
        self.use_spot_until_deadline = 0
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        deadline = self.deadline
        task_duration = self.task_duration
        
        work_done = 0
        for start, end in self.task_done_time:
            work_done += (end - start)
        work_remaining = task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE
            
        time_remaining = deadline - current_time
        
        gap = self.env.gap_seconds
        restart = self.restart_overhead
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.overhead_remaining = restart
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 0.5)
            
        if self.overhead_remaining > 0:
            self.overhead_remaining = max(0, self.overhead_remaining - gap)
            if self.overhead_remaining > 0:
                return ClusterType.NONE
        
        if not has_spot:
            self.spot_unavailable_streak += 1
        else:
            self.spot_unavailable_streak = 0
        
        required_time_od = work_remaining
        available_time = time_remaining - self.overhead_remaining
        
        if available_time <= 0:
            return ClusterType.ON_DEMAND if work_remaining > 0 else ClusterType.NONE
            
        urgency = required_time_od / max(available_time, 0.1)
        
        safety_margin = self.min_safety_margin + (1 - self.aggressiveness) * 2.0
        safety_margin *= (1 + self.consecutive_spot_failures * 0.3)
        
        if self.use_spot_until_deadline > 0:
            self.use_spot_until_deadline -= gap
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND if urgency > 1.0 else ClusterType.NONE
        
        spot_risk = 1.0 if has_spot else 0.0
        if self.spot_unavailable_streak > 10:
            spot_risk *= 0.3
        
        expected_spot_time = work_remaining + (restart if spot_risk > 0.7 else 0)
        spot_feasible = expected_spot_time <= available_time * (1.0 + safety_margin)
        
        if urgency > 1.2:
            return ClusterType.ON_DEMAND
        elif urgency > 1.0:
            if has_spot and spot_feasible:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        elif urgency > 0.8:
            if has_spot and spot_feasible and self.consecutive_spot_failures < 3:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND if work_remaining > 0 else ClusterType.NONE
        else:
            if has_spot and spot_feasible and self.spot_unavailable_streak < 5:
                self.use_spot_until_deadline = min(3600, time_remaining * 0.3)
                return ClusterType.SPOT
            elif has_spot and spot_feasible:
                return ClusterType.SPOT
            elif work_remaining > 0 and time_remaining > required_time_od * 1.5:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND if work_remaining > 0 else ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)