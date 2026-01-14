import json
from argparse import Namespace
from typing import List
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        
        self.time_step = None
        self.spot_price = 0.9701
        self.on_demand_price = 3.06
        self.price_ratio = self.spot_price / self.on_demand_price
        
        self.spot_history = []
        self.region_history = []
        self.consecutive_none_count = 0
        self.last_action = None
        self.switch_pending = False
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.time_step is None:
            self.time_step = self.env.gap_seconds
        
        current_region = self.env.get_current_region()
        
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        remaining_work = self.task_duration - sum(self.task_done_time)
        restart_overhead = self.restart_overhead
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        remaining_time = deadline - elapsed
        safe_remaining_time = remaining_time - restart_overhead
        
        if safe_remaining_time <= 0:
            return ClusterType.ON_DEMAND if remaining_work > 0 else ClusterType.NONE
        
        if remaining_work > safe_remaining_time:
            return ClusterType.ON_DEMAND
        
        if self.switch_pending:
            self.switch_pending = False
            return ClusterType.NONE
        
        num_regions = self.env.get_num_regions()
        
        if has_spot and self.consecutive_none_count < 2:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            
            if last_cluster_type == ClusterType.NONE:
                self.consecutive_none_count += 1
                
                if remaining_work > (remaining_time - self.time_step * 3):
                    return ClusterType.SPOT
                
                if self.consecutive_none_count >= 2:
                    return ClusterType.SPOT
                return ClusterType.NONE
            
            if last_cluster_type == ClusterType.ON_DEMAND:
                if remaining_work > (remaining_time - restart_overhead) * 0.8:
                    return ClusterType.ON_DEMAND
                
                if remaining_time > remaining_work * 1.5:
                    overhead_ratio = restart_overhead / self.time_step
                    if overhead_ratio > 0.3:
                        return ClusterType.NONE
                    else:
                        return ClusterType.SPOT
                return ClusterType.SPOT
        
        elif not has_spot:
            if last_cluster_type == ClusterType.SPOT:
                best_region = current_region
                max_future = 0
                
                for r in range(num_regions):
                    if r == current_region:
                        continue
                    
                    future_gain = 0
                    if r < len(self.spot_history):
                        future_gain = sum(self.spot_history[r][-3:]) if len(self.spot_history[r]) >= 3 else 0
                    
                    if future_gain > max_future:
                        max_future = future_gain
                        best_region = r
                
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    self.switch_pending = True
                    return ClusterType.NONE
            
            if remaining_work > (remaining_time - restart_overhead) * 0.7:
                return ClusterType.ON_DEMAND
            
            self.consecutive_none_count += 1
            if self.consecutive_none_count > 3:
                for r in range(num_regions):
                    if r == current_region:
                        continue
                    self.env.switch_region(r)
                    self.switch_pending = True
                    self.consecutive_none_count = 0
                    return ClusterType.NONE
            
            return ClusterType.NONE
        
        else:
            if remaining_work > (remaining_time - restart_overhead) * 0.6:
                return ClusterType.ON_DEMAND
            
            if last_cluster_type == ClusterType.ON_DEMAND:
                cost_saved = (self.on_demand_price - self.spot_price) * (self.time_step / 3600)
                time_cost = restart_overhead / 3600 * self.on_demand_price
                
                if cost_saved > time_cost * 2 and remaining_time > remaining_work * 2:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            
            return ClusterType.NONE

    def _record_decision(self, region: int, spot_available: bool, decision: ClusterType):
        if len(self.spot_history) <= region:
            for _ in range(region - len(self.spot_history) + 1):
                self.spot_history.append([])
        
        self.spot_history[region].append(1 if spot_available else 0)
        if len(self.spot_history[region]) > 10:
            self.spot_history[region] = self.spot_history[region][-10:]
        
        if decision != ClusterType.NONE:
            self.consecutive_none_count = 0
        
        self.last_action = decision
        self.region_history.append(region)