import json
from argparse import Namespace
from typing import List, Tuple
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_multi_region"

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
        
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.ondemand_price / self.spot_price
        
        self.regions_history = {}
        self.consecutive_failures = 0
        self.last_decision = ClusterType.NONE
        self.region_switches = 0
        self.emergency_mode = False
        
        return self

    def _should_switch_region(self, current_region: int, has_spot: bool) -> Tuple[bool, int]:
        num_regions = self.env.get_num_regions()
        best_region = current_region
        best_score = -float('inf')
        
        if not has_spot:
            for r in range(num_regions):
                if r == current_region:
                    continue
                    
                region_key = f"region_{r}"
                if region_key not in self.regions_history:
                    self.regions_history[region_key] = {
                        'spot_attempts': 0,
                        'spot_success': 0,
                        'last_seen': -1
                    }
                
                hist = self.regions_history[region_key]
                if hist['spot_attempts'] == 0:
                    success_rate = 0.5
                else:
                    success_rate = hist['spot_success'] / hist['spot_attempts']
                
                time_since_last = self.env.elapsed_seconds - hist['last_seen']
                recency_bonus = 1.0 / (1.0 + time_since_last / 3600.0)
                
                score = success_rate + 0.3 * recency_bonus
                
                if score > best_score:
                    best_score = score
                    best_region = r
        
        return best_region != current_region, best_region

    def _calculate_safety_margin(self) -> float:
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        if remaining_work <= 0:
            return float('inf')
        
        time_per_unit_ondemand = remaining_time / remaining_work
        time_per_unit_spot = (remaining_time - self.restart_overhead) / remaining_work
        
        critical_ratio = 1.5
        if remaining_time / self.task_duration < 2.0:
            critical_ratio = 1.2
        if remaining_time / self.task_duration < 1.5:
            critical_ratio = 1.0
        
        return critical_ratio * self.restart_overhead

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        region_key = f"region_{current_region}"
        if region_key not in self.regions_history:
            self.regions_history[region_key] = {
                'spot_attempts': 0,
                'spot_success': 0,
                'last_seen': self.env.elapsed_seconds
            }
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        safety_margin = self._calculate_safety_margin()
        time_needed_ondemand = remaining_work
        time_needed_spot = remaining_work + safety_margin
        
        if remaining_time <= time_needed_ondemand:
            self.emergency_mode = True
            return ClusterType.ON_DEMAND
        
        if self.emergency_mode:
            if remaining_time > time_needed_ondemand * 1.2:
                self.emergency_mode = False
            else:
                return ClusterType.ON_DEMAND
        
        should_switch, best_region = self._should_switch_region(current_region, has_spot)
        
        if should_switch and remaining_time > time_needed_spot + self.restart_overhead:
            self.env.switch_region(best_region)
            self.region_switches += 1
            
            new_region_key = f"region_{best_region}"
            if new_region_key not in self.regions_history:
                self.regions_history[new_region_key] = {
                    'spot_attempts': 0,
                    'spot_success': 0,
                    'last_seen': self.env.elapsed_seconds
                }
            
            current_region = best_region
            region_key = new_region_key
        
        self.regions_history[region_key]['last_seen'] = self.env.elapsed_seconds
        
        if remaining_time <= time_needed_spot:
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if self.consecutive_failures > 2 and remaining_time < time_needed_spot * 1.5:
                self.regions_history[region_key]['spot_attempts'] += 1
                return ClusterType.ON_DEMAND
            
            spot_risk = 0.0
            hist = self.regions_history[region_key]
            if hist['spot_attempts'] > 0:
                spot_risk = 1.0 - (hist['spot_success'] / hist['spot_attempts'])
            
            risk_threshold = 0.7 - (0.3 * (remaining_time / self.deadline))
            
            if spot_risk < risk_threshold:
                self.regions_history[region_key]['spot_attempts'] += 1
                self.consecutive_failures = 0
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
        
        self.consecutive_failures += 1
        
        if remaining_time > time_needed_ondemand * 1.1:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    def _on_spot_success(self):
        current_region = self.env.get_current_region()
        region_key = f"region_{current_region}"
        if region_key in self.regions_history:
            self.regions_history[region_key]['spot_success'] += 1
            self.consecutive_failures = max(0, self.consecutive_failures - 1)

    def _on_spot_failure(self):
        current_region = self.env.get_current_region()
        region_key = f"region_{current_region}"
        if region_key in self.regions_history:
            self.consecutive_failures += 1