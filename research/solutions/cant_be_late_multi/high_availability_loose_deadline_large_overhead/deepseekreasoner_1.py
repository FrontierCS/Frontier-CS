import json
import math
from argparse import Namespace
from typing import List

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
        
        self.gap_hours = None
        self.region_history = {}
        self.consecutive_failures = 0
        self.last_action = None
        self.budget_factor = 1.2
        self.spot_fallback_threshold = 0.7
        self.emergency_mode = False
        
        return self

    def _compute_remaining_work(self) -> float:
        return self.task_duration - sum(self.task_done_time)

    def _compute_time_remaining(self) -> float:
        return self.deadline - self.env.elapsed_seconds

    def _compute_critical_ratio(self) -> float:
        remaining_work = self._compute_remaining_work()
        time_remaining = self._compute_time_remaining()
        
        if time_remaining <= 0:
            return float('inf')
        
        min_time_needed = remaining_work + self.restart_overhead
        return min_time_needed / time_remaining

    def _get_best_region_spot_probability(self, current_region: int) -> float:
        if not hasattr(self, 'region_spot_availability'):
            self.region_spot_availability = [0.5] * self.env.get_num_regions()
        
        best_prob = 0.0
        for i in range(self.env.get_num_regions()):
            if i == current_region:
                continue
            if self.region_spot_availability[i] > best_prob:
                best_prob = self.region_spot_availability[i]
        return best_prob

    def _update_region_history(self, region: int, used_spot: bool, success: bool):
        if region not in self.region_history:
            self.region_history[region] = {'spot_attempts': 0, 'spot_success': 0}
        
        if used_spot:
            self.region_history[region]['spot_attempts'] += 1
            if success:
                self.region_history[region]['spot_success'] += 1
                self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1
        
        if self.region_history[region]['spot_attempts'] > 0:
            self.region_spot_availability[region] = (
                self.region_history[region]['spot_success'] / 
                self.region_history[region]['spot_attempts']
            )

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.gap_hours is None:
            self.gap_hours = self.env.gap_seconds / 3600.0
        
        remaining_work = self._compute_remaining_work()
        time_remaining = self._compute_time_remaining()
        current_region = self.env.get_current_region()
        
        self._update_region_history(
            current_region, 
            last_cluster_type == ClusterType.SPOT,
            last_cluster_type == ClusterType.SPOT and has_spot
        )
        
        critical_ratio = self._compute_critical_ratio()
        
        if critical_ratio > 1.0:
            self.emergency_mode = True
        
        if critical_ratio > self.spot_fallback_threshold:
            if has_spot and remaining_work > self.restart_overhead * 2:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        if self.emergency_mode:
            if time_remaining < remaining_work + self.restart_overhead:
                return ClusterType.ON_DEMAND
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        if self.consecutive_failures >= 2:
            num_regions = self.env.get_num_regions()
            for i in range(num_regions):
                next_region = (current_region + i + 1) % num_regions
                if next_region != current_region:
                    if (next_region in self.region_history and 
                        self.region_history[next_region].get('spot_success', 0) > 0):
                        self.env.switch_region(next_region)
                        self.consecutive_failures = 0
                        break
        
        if has_spot:
            if remaining_work > self.restart_overhead * 3:
                return ClusterType.SPOT
            elif remaining_work > self.restart_overhead:
                time_per_step = min(self.gap_hours, time_remaining / 3600)
                if (remaining_work / 3600) <= time_per_step * 1.5:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT
        
        if time_remaining > (remaining_work / 3600) * self.budget_factor + 1.0:
            return ClusterType.NONE
        
        return ClusterType.ON_DEMAND