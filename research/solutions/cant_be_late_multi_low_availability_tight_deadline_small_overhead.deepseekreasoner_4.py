import json
from argparse import Namespace
import math
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cost_aware_deadline_scheduler"

    def __init__(self, args):
        super().__init__(args)
        self.region_stats = []
        self.last_decision = None
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.spot_availability_history = []
        self.region_switch_penalty = 0

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

    def _update_region_stats(self, current_region: int, has_spot: bool):
        if len(self.region_stats) <= current_region:
            for _ in range(current_region - len(self.region_stats) + 1):
                self.region_stats.append({
                    "spot_available_count": 0,
                    "total_steps": 0,
                    "last_spot_availability": False
                })
        
        self.region_stats[current_region]["total_steps"] += 1
        if has_spot:
            self.region_stats[current_region]["spot_available_count"] += 1
        self.region_stats[current_region]["last_spot_availability"] = has_spot

    def _get_spot_availability_probability(self, region_idx: int) -> float:
        if region_idx >= len(self.region_stats) or self.region_stats[region_idx]["total_steps"] == 0:
            return 0.0
        stats = self.region_stats[region_idx]
        return stats["spot_available_count"] / stats["total_steps"]

    def _get_remaining_work(self) -> float:
        total_done = sum(self.task_done_time)
        return max(0.0, self.task_duration - total_done)

    def _get_required_rate(self) -> float:
        remaining_work = self._get_remaining_work()
        time_left = self.deadline - self.env.elapsed_seconds
        
        if time_left <= 0:
            return float('inf')
        
        return remaining_work / time_left

    def _get_best_alternative_region(self, current_region: int) -> int:
        best_region = current_region
        best_prob = self._get_spot_availability_probability(current_region)
        
        for i in range(self.env.get_num_regions()):
            if i == current_region:
                continue
            prob = self._get_spot_availability_probability(i)
            if prob > best_prob:
                best_prob = prob
                best_region = i
        
        return best_region

    def _should_use_ondemand(self) -> bool:
        remaining_work = self._get_remaining_work()
        time_left = self.deadline - self.env.elapsed_seconds
        
        if time_left <= 0:
            return True
        
        remaining_steps = time_left / self.env.gap_seconds
        work_steps_needed = remaining_work / self.env.gap_seconds
        
        safety_margin = 2.0
        if remaining_steps - work_steps_needed < safety_margin:
            return True
        
        required_rate = self._get_required_rate()
        if required_rate > 0.8:
            return True
        
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        
        self._update_region_stats(current_region, has_spot)
        
        remaining_work = self._get_remaining_work()
        if remaining_work <= 0:
            return ClusterType.NONE
        
        time_left = self.deadline - self.env.elapsed_seconds
        
        if time_left <= 0:
            return ClusterType.NONE
        
        required_rate = self._get_required_rate()
        
        if self._should_use_ondemand():
            if self.remaining_restart_overhead > 0:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if self.remaining_restart_overhead > 0:
                return ClusterType.NONE
            
            if required_rate < 0.3:
                spot_prob = self._get_spot_availability_probability(current_region)
                if spot_prob < 0.5:
                    best_alt = self._get_best_alternative_region(current_region)
                    if best_alt != current_region:
                        self.env.switch_region(best_alt)
                        return ClusterType.NONE
            
            return ClusterType.SPOT
        else:
            if self.remaining_restart_overhead > 0:
                return ClusterType.NONE
            
            best_alt = self._get_best_alternative_region(current_region)
            if best_alt != current_region:
                self.env.switch_region(best_alt)
                return ClusterType.NONE
            
            if required_rate > 0.6:
                return ClusterType.ON_DEMAND
            
            return ClusterType.NONE
