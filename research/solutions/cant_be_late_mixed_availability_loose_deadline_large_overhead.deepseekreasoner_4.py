import math
import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.97
        self.on_demand_price = 3.06
        self.time_step = 3600  # 1 hour in seconds
        self.required_work_seconds = 48 * 3600  # 48 hours
        self.deadline_seconds = 70 * 3600  # 70 hours
        self.restart_overhead_hours = 0.20
        self.critical_threshold = 0.85
        self.aggressiveness = 0.7
        self.conservative_threshold = 0.3
        self.spot_availability_buffer = 3
        self.work_done = 0.0
        self.time_elapsed = 0.0
        self.spot_unavailable_count = 0
        self.consecutive_spot_available = 0
        self.last_decision = ClusterType.NONE
        self.restart_timer = 0.0
        self.work_accumulated = 0.0
        self.spot_history = []
        self.emergency_mode = False
        self.safety_margin = 4 * 3600  # 4 hours safety margin
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _update_state(self, last_cluster_type):
        self.time_elapsed = self.env.elapsed_seconds
        self.work_done = sum(end - start for start, end in self.task_done_time)
        self.restart_timer = max(0.0, self.restart_timer - self.env.gap_seconds)
        
        if last_cluster_type == ClusterType.SPOT:
            self.work_accumulated += self.env.gap_seconds
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.work_accumulated += self.env.gap_seconds
    
    def _calculate_time_pressure(self):
        remaining_work = max(0.0, self.task_duration - self.work_done)
        time_left = max(0.0, self.deadline - self.time_elapsed)
        
        if time_left <= 0:
            return 1.0
        
        if remaining_work <= 0:
            return 0.0
            
        min_time_needed = remaining_work
        if self.restart_timer > 0:
            min_time_needed += self.restart_timer
            
        return min(1.0, max(0.0, 1.0 - (time_left - self.safety_margin) / (min_time_needed + 1e-6)))
    
    def _should_use_spot(self, has_spot, time_pressure):
        if not has_spot:
            return False
            
        if time_pressure > self.critical_threshold:
            return False
            
        remaining_work = max(0.0, self.task_duration - self.work_done)
        time_left = max(0.0, self.deadline - self.time_elapsed)
        
        spot_efficiency = 0.8
        estimated_spot_time = remaining_work / spot_efficiency + self.restart_overhead * 2
        
        if time_left < estimated_spot_time:
            return False
            
        if self.spot_unavailable_count > 5:
            return False
            
        return True
    
    def _should_use_ondemand(self, time_pressure):
        if time_pressure > self.conservative_threshold:
            return True
            
        remaining_work = max(0.0, self.task_duration - self.work_done)
        time_left = max(0.0, self.deadline - self.time_elapsed)
        
        if time_left < remaining_work * 1.5:
            return True
            
        if self.emergency_mode:
            return True
            
        return False
    
    def _calculate_risk_score(self, has_spot):
        remaining_work = max(0.0, self.task_duration - self.work_done)
        time_left = max(0.0, self.deadline - self.time_elapsed)
        
        if time_left <= 0 or remaining_work <= 0:
            return 0.0
            
        optimal_ondemand_time = remaining_work
        optimal_spot_time = remaining_work / 0.8 + self.restart_overhead * 2
        
        time_ratio = time_left / optimal_ondemand_time
        work_ratio = remaining_work / self.task_duration
        
        risk_score = (1.0 - time_ratio) * 0.6 + work_ratio * 0.4
        
        if not has_spot:
            risk_score *= 1.2
            
        return min(1.0, max(0.0, risk_score))
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_state(last_cluster_type)
        
        remaining_work = max(0.0, self.task_duration - self.work_done)
        time_left = max(0.0, self.deadline - self.time_elapsed)
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        if time_left <= 0:
            return ClusterType.NONE
            
        time_pressure = self._calculate_time_pressure()
        risk_score = self._calculate_risk_score(has_spot)
        
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 10:
            self.spot_history.pop(0)
            
        spot_availability_rate = sum(self.spot_history) / len(self.spot_history) if self.spot_history else 0
        
        if has_spot:
            self.consecutive_spot_available += 1
            self.spot_unavailable_count = 0
        else:
            self.consecutive_spot_available = 0
            self.spot_unavailable_count += 1
            
        if time_pressure > 0.9 or (time_left < remaining_work * 1.2):
            self.emergency_mode = True
            
        if self.emergency_mode:
            if remaining_work > 0 and time_left > 0:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
            
        if self.restart_timer > 0:
            return ClusterType.NONE
            
        if self._should_use_ondemand(time_pressure):
            if remaining_work > 0:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
            
        if self._should_use_spot(has_spot, time_pressure):
            if spot_availability_rate > 0.6 and self.consecutive_spot_available >= 2:
                return ClusterType.SPOT
            elif spot_availability_rate > 0.4 and risk_score < 0.5:
                return ClusterType.SPOT
                
        if remaining_work > 0 and time_left > 0:
            if has_spot and risk_score < 0.3:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
                
        return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)