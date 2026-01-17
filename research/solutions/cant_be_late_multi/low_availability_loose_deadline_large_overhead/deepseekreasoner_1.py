import json
from argparse import Namespace
import math
from typing import List, Tuple
from collections import deque

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_multi_region"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_history = []
        self.region_spot_availability = {}
        self.last_region = -1
        self.consecutive_failures = 0
        self.max_switch_attempts = 3
        self.switch_counter = 0
        self.emergency_od_threshold = 0.2
        self.patience_counter = 0
        self.max_patience = 5
        
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
        
        self.num_regions = 0
        self.spot_prices = []
        self.od_prices = []
        
        return self
    
    def _get_remaining_work(self) -> float:
        return max(0.0, self.task_duration - sum(self.task_done_time))
    
    def _get_time_remaining(self) -> float:
        return max(0.0, self.deadline - self.env.elapsed_seconds)
    
    def _get_critical_ratio(self) -> float:
        remaining_work = self._get_remaining_work()
        time_remaining = self._get_time_remaining()
        
        if time_remaining <= 0:
            return float('inf')
        
        required_time = remaining_work + self.restart_overhead
        return required_time / time_remaining if time_remaining > 0 else float('inf')
    
    def _should_use_ondemand(self) -> bool:
        critical_ratio = self._get_critical_ratio()
        remaining_work = self._get_remaining_work()
        time_remaining = self._get_time_remaining()
        
        if critical_ratio > 0.7:
            return True
        
        if time_remaining - remaining_work < 2 * self.restart_overhead:
            return True
            
        if self.consecutive_failures >= self.max_switch_attempts:
            return True
            
        if remaining_work / time_remaining > 0.8:
            return True
            
        return False
    
    def _find_best_region(self, current_region: int, has_spot: bool) -> int:
        num_regions = self.env.get_num_regions()
        
        if has_spot and self.consecutive_failures == 0:
            return current_region
        
        best_region = current_region
        best_score = -1
        
        for region in range(num_regions):
            if region == current_region:
                continue
                
            if region in self.region_spot_availability:
                recent_availability = self.region_spot_availability[region][-10:]
                if recent_availability:
                    availability_score = sum(recent_availability) / len(recent_availability)
                    
                    if availability_score > best_score:
                        best_score = availability_score
                        best_region = region
        
        if best_score > 0.5 or self.consecutive_failures > 0:
            return best_region
            
        return current_region
    
    def _update_spot_history(self, region: int, has_spot: bool):
        if region not in self.region_spot_availability:
            self.region_spot_availability[region] = deque(maxlen=50)
        self.region_spot_availability[region].append(1 if has_spot else 0)
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        
        if self.last_region != current_region:
            self.last_region = current_region
            self.consecutive_failures = 0
            self.patience_counter = 0
        
        self._update_spot_history(current_region, has_spot)
        
        remaining_work = self._get_remaining_work()
        time_remaining = self._get_time_remaining()
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        if time_remaining <= 0:
            return ClusterType.NONE
        
        if time_remaining < remaining_work:
            return ClusterType.ON_DEMAND
        
        if self._should_use_ondemand():
            self.consecutive_failures = 0
            self.patience_counter = 0
            return ClusterType.ON_DEMAND
        
        if has_spot:
            self.consecutive_failures = 0
            self.patience_counter = 0
            best_region = self._find_best_region(current_region, has_spot)
            
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.last_region = best_region
                
            return ClusterType.SPOT
        else:
            self.consecutive_failures += 1
            self.patience_counter += 1
            
            if self.patience_counter >= self.max_patience:
                best_region = self._find_best_region(current_region, has_spot)
                
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    self.last_region = best_region
                    self.patience_counter = 0
                    self.consecutive_failures = 0
                    
                    return ClusterType.NONE
            
            if self.consecutive_failures >= self.max_switch_attempts:
                return ClusterType.ON_DEMAND
            
            return ClusterType.NONE