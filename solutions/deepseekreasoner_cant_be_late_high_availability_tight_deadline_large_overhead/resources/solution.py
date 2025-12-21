import os
import json
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
from typing import Dict, Any
import numpy as np


class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.remaining_work = None
        self.spot_history = []
        self.spot_availability_rate = 0.6
        self.conservative_threshold = 0.85
        self.emergency_threshold = 0.95
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.max_spot_streak = 0
        self.current_spot_streak = 0
        self.adaptation_rate = 0.1
        self.use_hybrid = True
        self.config = None
        
    def solve(self, spec_path: str) -> "Solution":
        if os.path.exists(spec_path):
            try:
                with open(spec_path, 'r') as f:
                    self.config = json.load(f)
                    if "conservative_threshold" in self.config:
                        self.conservative_threshold = self.config["conservative_threshold"]
                    if "emergency_threshold" in self.config:
                        self.emergency_threshold = self.config["emergency_threshold"]
                    if "adaptation_rate" in self.config:
                        self.adaptation_rate = self.config["adaptation_rate"]
                    if "use_hybrid" in self.config:
                        self.use_hybrid = self.config["use_hybrid"]
            except:
                pass
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
            
        if len(self.spot_history) > 10:
            self.spot_availability_rate = (
                0.9 * self.spot_availability_rate + 
                0.1 * np.mean(self.spot_history[-10:])
            )
        
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.current_spot_streak += 1
            self.max_spot_streak = max(self.max_spot_streak, self.current_spot_streak)
        else:
            self.current_spot_streak = 0
        
        total_work = self.task_duration
        work_done = sum(self.task_done_time)
        self.remaining_work = total_work - work_done
        
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        deadline = self.deadline
        time_left = deadline - elapsed
        
        restart_time = self.restart_overhead if (
            last_cluster_type == ClusterType.SPOT and 
            not has_spot and 
            self.remaining_work > 0
        ) else 0
        
        effective_time_left = time_left - restart_time
        
        required_time = self.remaining_work
        
        if effective_time_left <= 0:
            return ClusterType.ON_DEMAND
        
        if effective_time_left < required_time:
            return ClusterType.ON_DEMAND
        
        progress_ratio = work_done / total_work if total_work > 0 else 0
        time_ratio = elapsed / deadline if deadline > 0 else 0
        
        critical_phase = progress_ratio < time_ratio
        
        buffer_hours = 4.0
        buffer_seconds = buffer_hours * 3600
        safety_margin = buffer_seconds * 0.7
        
        if time_left - required_time < safety_margin:
            critical_phase = True
        
        if critical_phase:
            if has_spot and self.spot_availability_rate > 0.7:
                if self.max_spot_streak > 5 and self.current_spot_streak > 2:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        if not has_spot:
            return ClusterType.NONE
        
        if self.use_hybrid:
            if time_left > required_time * 1.5:
                hybrid_ratio = self.spot_price / self.ondemand_price
                if hybrid_ratio < 0.5:
                    return ClusterType.SPOT
                else:
                    if np.random.random() < 0.7:
                        return ClusterType.SPOT
                    else:
                        return ClusterType.ON_DEMAND
            else:
                if np.random.random() < 0.8:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        
        spot_confidence = min(1.0, self.max_spot_streak * 0.1)
        
        if time_left > required_time * 2:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        elif time_left > required_time * 1.2:
            if has_spot and spot_confidence > 0.5:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            if has_spot and spot_confidence > 0.8:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
