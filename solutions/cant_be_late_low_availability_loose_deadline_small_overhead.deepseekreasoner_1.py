import json
import math
from typing import List, Tuple, Dict
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "dynamic_threshold"

    def __init__(self, args):
        super().__init__(args)
        self.config = {}
        self.spot_window = 0
        self.spot_availability_history = []
        self.consecutive_spot_failures = 0
        self.safety_margin = 0.05
        self.last_action = ClusterType.NONE
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                self.config = json.load(f)
        except:
            pass
        
        self.spot_window = 0
        self.spot_availability_history = []
        self.consecutive_spot_failures = 0
        self.safety_margin = 0.05
        self.last_action = ClusterType.NONE
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.last_action = last_cluster_type
        
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        task_duration = self.task_duration
        restart_overhead = self.restart_overhead
        
        total_done = sum(self.task_done_time)
        remaining_work = task_duration - total_done
        time_left = deadline - current_time
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
            
        if not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
        
        spot_reliability = sum(self.spot_availability_history) / max(1, len(self.spot_availability_history))
        
        effective_time_needed = remaining_work
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            effective_time_needed += restart_overhead
        
        critical_ratio = effective_time_needed / max(0.001, time_left)
        
        urgency = max(0, 1 - (time_left / (deadline * 0.8)))
        
        time_budget_ratio = time_left / effective_time_needed if effective_time_needed > 0 else float('inf')
        
        if time_budget_ratio < 1.1:
            return ClusterType.ON_DEMAND
        
        if time_budget_ratio < 1.3:
            if has_spot and spot_reliability > 0.6 and self.consecutive_spot_failures < 3:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        if critical_ratio > 0.8:
            if has_spot and spot_reliability > 0.4 and self.consecutive_spot_failures < 5:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        if critical_ratio > 0.5:
            if has_spot and spot_reliability > 0.3 and self.consecutive_spot_failures < 8:
                return ClusterType.SPOT
            if time_budget_ratio > 1.5 and has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND if not has_spot else ClusterType.SPOT
        
        if time_budget_ratio > 2.0:
            if has_spot and self.consecutive_spot_failures < 10:
                self.spot_window += 1
                if self.spot_window >= 2 or spot_reliability > 0.2:
                    return ClusterType.SPOT
                else:
                    return ClusterType.NONE
            else:
                self.spot_window = 0
                return ClusterType.NONE
        else:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
