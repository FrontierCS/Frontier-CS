import argparse
import math
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.safety_margin = None
        self.critical_threshold = None
        self.restart_buffer = None
        self.spot_use_threshold = None
        self.initialized = False

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, 'r') as f:
            lines = f.readlines()
            prices = {}
            for line in lines:
                if line.startswith('spot_price'):
                    prices['spot'] = float(line.split('=')[1].strip())
                elif line.startswith('on_demand_price'):
                    prices['on_demand'] = float(line.split('=')[1].strip())
        
        if prices:
            spot_price = prices.get('spot', 0.97)
            on_demand_price = prices.get('on_demand', 3.06)
            
            price_ratio = spot_price / on_demand_price
            self.spot_use_threshold = max(0.3, min(0.7, price_ratio))
        else:
            self.spot_use_threshold = 0.32
        
        self.safety_margin = 3600
        self.critical_threshold = 7200
        self.restart_buffer = 1800
        self.initialized = True
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            self.spot_use_threshold = 0.32
            self.safety_margin = 3600
            self.critical_threshold = 7200
            self.restart_buffer = 1800
            self.initialized = True

        current_time = self.env.elapsed_seconds
        time_step = self.env.gap_seconds
        
        remaining_work = self.task_duration - sum(
            end - start for start, end in self.task_done_time
        )
        time_to_deadline = self.deadline - current_time
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        if time_to_deadline <= 0:
            return ClusterType.ON_DEMAND
        
        work_rate = 1.0
        effective_time = time_to_deadline
        
        if last_cluster_type != ClusterType.NONE:
            effective_time -= self.restart_overhead
        
        time_needed_on_demand = remaining_work / work_rate + self.restart_overhead
        is_critical = time_to_deadline - time_needed_on_demand <= self.critical_threshold
        
        if is_critical:
            if has_spot and (time_to_deadline - remaining_work / work_rate > 
                           self.restart_overhead + self.restart_buffer):
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        if not has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.NONE
            if time_to_deadline - remaining_work / work_rate < self.safety_margin:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        if last_cluster_type == ClusterType.NONE:
            if time_to_deadline - remaining_work / work_rate > self.restart_overhead + 3600:
                return ClusterType.SPOT
            if time_to_deadline - remaining_work / work_rate > self.restart_overhead + 1800:
                return ClusterType.ON_DEMAND
        
        if last_cluster_type == ClusterType.SPOT:
            if time_to_deadline - remaining_work / work_rate > self.restart_overhead * 2:
                return ClusterType.SPOT
        
        if time_to_deadline - remaining_work / work_rate < self.safety_margin:
            return ClusterType.ON_DEMAND
        
        return ClusterType.SPOT if has_spot else ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)