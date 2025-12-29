import json
from argparse import Namespace
import math
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_spot_optimizer"

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
        
        self.initialized = False
        self.current_region = 0
        self.consecutive_no_spot = 0
        self.num_regions = 0
        self.region_history = []
        self.last_action = None
        self.spot_attempts = 0
        self.on_demand_used = False
        self.critical_threshold = 0.15
        
        return self

    def _initialize_state(self):
        self.num_regions = self.env.get_num_regions()
        self.current_region = self.env.get_current_region()
        self.region_history = [0] * self.num_regions
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            self._initialize_state()
        
        self.current_region = self.env.get_current_region()
        
        time_left = self.deadline - self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        
        if work_left <= 0:
            return ClusterType.NONE
            
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        hours_left = time_left / 3600.0
        hours_work_left = work_left / 3600.0
        
        if hours_work_left <= 0:
            return ClusterType.NONE
        
        progress_ratio = 1.0 - (work_left / self.task_duration)
        time_ratio = self.env.elapsed_seconds / self.deadline
        
        urgent = hours_work_left > hours_left * (1.0 + self.critical_threshold)
        
        if urgent:
            self.on_demand_used = True
            return ClusterType.ON_DEMAND
        
        if has_spot:
            spot_score = self._calculate_spot_score(hours_work_left, hours_left)
            
            if spot_score > 0.3 or not self.on_demand_used:
                self.spot_attempts += 1
                self.consecutive_no_spot = 0
                self.region_history[self.current_region] += 1
                return ClusterType.SPOT
        
        self.consecutive_no_spot += 1
        
        if self.consecutive_no_spot >= 2 and self.num_regions > 1:
            best_region = self._find_best_region()
            if best_region != self.current_region:
                self.env.switch_region(best_region)
                self.current_region = best_region
                self.consecutive_no_spot = 0
        
        if hours_work_left > hours_left * 0.9:
            self.on_demand_used = True
            return ClusterType.ON_DEMAND
        
        if has_spot:
            return ClusterType.SPOT
        
        return ClusterType.NONE

    def _calculate_spot_score(self, hours_work_left: float, hours_left: float) -> float:
        if hours_left <= 0:
            return 0.0
        
        time_pressure = hours_work_left / hours_left if hours_left > 0 else float('inf')
        
        base_score = 0.7
        
        if time_pressure > 1.5:
            base_score *= 0.3
        elif time_pressure > 1.2:
            base_score *= 0.6
        elif time_pressure > 1.0:
            base_score *= 0.8
        
        progress = 1.0 - (hours_work_left / (self.task_duration / 3600.0))
        if progress > 0.8:
            base_score *= 1.2
        elif progress > 0.5:
            base_score *= 1.1
        
        return min(max(base_score, 0.0), 1.0)

    def _find_best_region(self) -> int:
        current_time = self.env.elapsed_seconds / 3600.0
        
        scores = []
        for i in range(self.num_regions):
            if i == self.current_region:
                score = -self.consecutive_no_spot * 0.5
            else:
                score = 0.0
            
            if self.region_history[i] < 1:
                score += 2.0
            else:
                score += 1.0 / (self.region_history[i] + 1)
            
            scores.append((score, i))
        
        scores.sort(reverse=True)
        return scores[0][1]