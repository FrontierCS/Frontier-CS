import json
from argparse import Namespace
from enum import Enum
from typing import List, Tuple
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class State(Enum):
    INIT = 0
    SPOT = 1
    ON_DEMAND = 2
    PAUSED = 3


class Solution(MultiRegionStrategy):
    NAME = "efficient_scheduler"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.state = State.INIT
        self.current_region = 0
        self.region_stats = []
        self.time_step = 3600  # 1 hour in seconds
        self.consecutive_spot_fails = 0
        self.max_spot_fails = 3
        self.region_switch_cooldown = 0
        self.work_done = 0.0
        
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
        return self

    def _initialize_region_stats(self):
        num_regions = self.env.get_num_regions()
        self.region_stats = [{
            'spot_availability': 0,
            'spot_count': 0,
            'last_used': -1,
            'consecutive_fails': 0
        } for _ in range(num_regions)]

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        if has_spot:
            self.region_stats[region_idx]['spot_availability'] += 1
            self.region_stats[region_idx]['spot_count'] += 1
            self.region_stats[region_idx]['consecutive_fails'] = 0
        else:
            self.region_stats[region_idx]['consecutive_fails'] += 1
        self.region_stats[region_idx]['last_used'] = self.env.elapsed_seconds

    def _get_best_spot_region(self) -> int:
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        best_region = current_region
        best_score = -float('inf')
        
        for i in range(num_regions):
            if i == current_region:
                continue
                
            stats = self.region_stats[i]
            availability_score = stats['spot_availability']
            recency_penalty = (self.env.elapsed_seconds - stats['last_used']) / self.time_step
            fail_penalty = stats['consecutive_fails'] * 10
            
            score = availability_score - recency_penalty - fail_penalty
            
            if score > best_score:
                best_score = score
                best_region = i
                
        return best_region

    def _calculate_urgency(self) -> float:
        time_remaining = self.deadline - self.env.elapsed_seconds
        work_remaining = self.task_duration - sum(self.task_done_time)
        
        if work_remaining <= 0:
            return 0.0
            
        min_time_needed = work_remaining
        if self.remaining_restart_overhead > 0:
            min_time_needed += self.remaining_restart_overhead
            
        return max(0.0, time_remaining - min_time_needed) / self.time_step

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, 'region_stats'):
            self._initialize_region_stats()
            
        current_region = self.env.get_current_region()
        self._update_region_stats(current_region, has_spot)
        
        urgency = self._calculate_urgency()
        work_remaining = self.task_duration - sum(self.task_done_time)
        
        if work_remaining <= 0:
            return ClusterType.NONE
            
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
            
        if self.region_switch_cooldown > 0:
            self.region_switch_cooldown -= 1
            
        should_switch_region = False
        
        if not has_spot and self.state == State.SPOT:
            self.consecutive_spot_fails += 1
            if self.consecutive_spot_fails >= self.max_spot_fails:
                should_switch_region = True
                self.consecutive_spot_fails = 0
        else:
            self.consecutive_spot_fails = 0
            
        if should_switch_region and self.region_switch_cooldown == 0:
            best_region = self._get_best_spot_region()
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.region_switch_cooldown = 2
                self.state = State.INIT
                return ClusterType.NONE
        
        time_remaining = self.deadline - self.env.elapsed_seconds
        work_remaining = self.task_duration - sum(self.task_done_time)
        
        min_time_with_od = work_remaining
        min_time_with_spot = work_remaining + self.restart_overhead
        
        critical_time = min_time_with_od + 2 * self.time_step
        
        if time_remaining < critical_time:
            self.state = State.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        if has_spot and urgency > 2:
            self.state = State.SPOT
            return ClusterType.SPOT
        elif has_spot and last_cluster_type == ClusterType.SPOT:
            self.state = State.SPOT
            return ClusterType.SPOT
        elif has_spot and self.state != State.ON_DEMAND:
            self.state = State.SPOT
            return ClusterType.SPOT
        elif not has_spot and urgency > 4:
            self.state = State.ON_DEMAND
            return ClusterType.ON_DEMAND
        else:
            self.state = State.PAUSED
            return ClusterType.NONE