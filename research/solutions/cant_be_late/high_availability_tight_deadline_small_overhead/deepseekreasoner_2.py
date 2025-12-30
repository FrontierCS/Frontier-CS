import argparse
import math
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_safety_margin"

    def __init__(self, args):
        super().__init__(args)
        self.safety_margin_factor = 1.2
        self.min_safety_margin = 1800
        self.spot_availability_history = []
        self.consecutive_spot_failures = 0
        self.max_consecutive_failures = 5
        self.work_remaining_history = []
        self.last_decision = ClusterType.NONE
        self.restart_timer = 0
        self.spot_usage_count = 0
        self.od_usage_count = 0
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _update_state(self, last_cluster_type: ClusterType, has_spot: bool):
        """Update internal state based on previous step"""
        self.spot_availability_history.append(has_spot)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
            
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
            
        if last_cluster_type == ClusterType.SPOT:
            self.spot_usage_count += 1
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.od_usage_count += 1
            
        if self.restart_timer > 0:
            self.restart_timer = max(0, self.restart_timer - self.env.gap_seconds)
            
        self.last_decision = last_cluster_type
        
    def _calculate_work_remaining(self) -> float:
        """Calculate remaining work in seconds"""
        total_done = sum(segment for segment in self.task_done_time)
        return max(0.0, self.task_duration - total_done)
    
    def _calculate_time_remaining(self) -> float:
        """Calculate time until deadline in seconds"""
        return max(0.0, self.deadline - self.env.elapsed_seconds)
    
    def _calculate_safety_margin(self, work_remaining: float, time_remaining: float) -> float:
        """Calculate dynamic safety margin based on current state"""
        base_margin = self.min_safety_margin
        
        if len(self.spot_availability_history) >= 20:
            spot_availability = sum(self.spot_availability_history[-20:]) / 20.0
            reliability_factor = 1.0 - spot_availability
            base_margin += reliability_factor * 3600
        
        progress_ratio = 1.0 - (work_remaining / self.task_duration)
        time_pressure = max(0.0, work_remaining - time_remaining) / work_remaining if work_remaining > 0 else 0
        pressure_factor = 1.0 + time_pressure * 2.0
        
        final_margin = base_margin * pressure_factor * self.safety_margin_factor
        return min(final_margin, time_remaining * 0.5)
    
    def _should_use_spot(self, work_remaining: float, time_remaining: float, has_spot: bool) -> bool:
        """Determine if spot should be used"""
        if not has_spot:
            return False
            
        if self.restart_timer > 0:
            return False
            
        if work_remaining <= 0:
            return False
            
        safety_margin = self._calculate_safety_margin(work_remaining, time_remaining)
        
        time_needed_on_spot = work_remaining + self.restart_overhead
        if self.consecutive_spot_failures >= self.max_consecutive_failures:
            time_needed_on_spot += self.restart_overhead * 2
            
        time_needed_on_demand = work_remaining
        
        has_enough_time_for_spot = time_remaining >= time_needed_on_spot + safety_margin
        has_enough_time_for_demand = time_remaining >= time_needed_on_demand
        
        if not has_enough_time_for_demand:
            return False
            
        spot_ratio = self.spot_usage_count / max(1, self.spot_usage_count + self.od_usage_count)
        if spot_ratio < 0.5 and has_enough_time_for_spot:
            return True
            
        cost_saving_threshold = 0.3
        if has_enough_time_for_spot:
            estimated_spot_time = work_remaining * (1.0 / 0.6)
            estimated_spot_cost = estimated_spot_time * 0.97 / 3600
            estimated_demand_cost = work_remaining * 3.06 / 3600
            
            if estimated_spot_cost < estimated_demand_cost * (1.0 - cost_saving_threshold):
                return True
                
        return has_enough_time_for_spot
    
    def _should_use_ondemand(self, work_remaining: float, time_remaining: float) -> bool:
        """Determine if on-demand should be used"""
        if work_remaining <= 0:
            return False
            
        if self.restart_timer > 0:
            return False
            
        time_needed = work_remaining
        has_enough_time = time_remaining >= time_needed
        
        if not has_enough_time:
            return True
            
        critical_threshold = work_remaining + self.restart_overhead * 2
        return time_remaining < critical_threshold
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_state(last_cluster_type, has_spot)
        
        work_remaining = self._calculate_work_remaining()
        time_remaining = self._calculate_time_remaining()
        
        if work_remaining <= 0:
            return ClusterType.NONE
            
        if self._should_use_ondemand(work_remaining, time_remaining):
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.restart_timer = self.restart_overhead
            return ClusterType.ON_DEMAND
            
        if self._should_use_spot(work_remaining, time_remaining, has_spot):
            if last_cluster_type != ClusterType.SPOT:
                self.restart_timer = self.restart_overhead
            return ClusterType.SPOT
            
        return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)