import os
import json
import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.safety_margin = None
        self.spot_history = []
        self.spot_availability = 0.0
        self.consecutive_spots = 0
        self.last_switch_time = 0
        self.min_spot_burst = 0
        self.use_spot_aggressively = True
        self.restart_penalty_time = 0
        self.phase = "initial"
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            if os.path.exists(spec_path):
                with open(spec_path, 'r') as f:
                    spec = json.load(f)
                    if "safety_margin" in spec:
                        self.safety_margin = spec["safety_margin"]
        except:
            pass
            
        if self.safety_margin is None:
            self.safety_margin = 0.15
            
        self.restart_penalty_time = self.restart_overhead
        return self
    
    def _calculate_remaining_time(self):
        elapsed = self.env.elapsed_seconds
        remaining = self.deadline - elapsed
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        work_left = self.task_duration - work_done
        return remaining, work_left, work_done
    
    def _should_switch_to_od(self, remaining, work_left):
        if work_left <= 0:
            return False
            
        time_per_work_unit = 1.0
        estimated_time_needed = work_left * time_per_work_unit
        
        if self.env.cluster_type == ClusterType.SPOT:
            estimated_time_needed += self.restart_penalty_time
            
        buffer = max(self.restart_penalty_time * 2, remaining * self.safety_margin)
        return estimated_time_needed > (remaining - buffer)
    
    def _update_spot_history(self, has_spot):
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
            
        if has_spot:
            self.consecutive_spots += 1
        else:
            self.consecutive_spots = 0
            
        if len(self.spot_history) > 0:
            self.spot_availability = sum(self.spot_history) / len(self.spot_history)
    
    def _calculate_dynamic_min_spot_burst(self):
        if self.spot_availability > 0.7:
            return 3
        elif self.spot_availability > 0.5:
            return 5
        else:
            return 8
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_spot_history(has_spot)
        
        remaining, work_left, work_done = self._calculate_remaining_time()
        
        if work_left <= 0:
            return ClusterType.NONE
        
        time_since_switch = self.env.elapsed_seconds - self.last_switch_time
        
        if self._should_switch_to_od(remaining, work_left):
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.last_switch_time = self.env.elapsed_seconds
            return ClusterType.ON_DEMAND
        
        if not has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.NONE
            elif (last_cluster_type == ClusterType.ON_DEMAND and 
                  remaining > work_left + self.restart_penalty_time * 3):
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
        
        if last_cluster_type == ClusterType.SPOT:
            if self.consecutive_spots < self._calculate_dynamic_min_spot_burst():
                return ClusterType.SPOT
            elif time_since_switch < self.restart_penalty_time * 1.5:
                return ClusterType.SPOT
            else:
                if remaining < work_left * 1.3 + self.restart_penalty_time:
                    return ClusterType.SPOT
                else:
                    return ClusterType.NONE
        elif last_cluster_type == ClusterType.ON_DEMAND:
            if remaining > work_left * 1.5 + self.restart_penalty_time * 2:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:  # NONE
            if self.consecutive_spots >= 2:
                self.last_switch_time = self.env.elapsed_seconds
                return ClusterType.SPOT
            elif remaining < work_left * 1.2:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)