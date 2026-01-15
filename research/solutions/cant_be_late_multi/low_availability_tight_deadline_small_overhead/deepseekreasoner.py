import json
from argparse import Namespace
import math
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "efficient_scheduler"

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
        
        self.total_regions = None
        self.region_spot_history = None
        self.consecutive_spot_failures = 0
        self.last_decision = None
        self.spot_attempt_count = 0
        self.spot_success_count = 0
        self.estimated_spot_prob = 0.5
        self.min_required_steps = None
        self.step_size = None
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.total_regions is None:
            self.total_regions = self.env.get_num_regions()
            self.region_spot_history = [[] for _ in range(self.total_regions)]
            self.step_size = self.env.gap_seconds
            
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        total_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_done
        
        if self.min_required_steps is None:
            self.min_required_steps = math.ceil(remaining_work / self.step_size)
        
        if remaining_time <= 0 or remaining_work <= 0:
            return ClusterType.NONE
            
        if remaining_time < self.restart_overhead:
            return ClusterType.NONE
            
        if remaining_work <= self.step_size:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        time_per_step = self.step_size
        if last_cluster_type != ClusterType.NONE and last_cluster_type != ClusterType.ON_DEMAND:
            if self.remaining_restart_overhead > 0:
                time_per_step = self.step_size - self.remaining_restart_overhead
        
        steps_needed = math.ceil(remaining_work / time_per_step)
        available_steps = math.floor(remaining_time / self.step_size)
        
        if available_steps < steps_needed:
            return ClusterType.ON_DEMAND
            
        if remaining_time < (steps_needed + 2) * self.step_size:
            return ClusterType.ON_DEMAND
        
        self.region_spot_history[current_region].append(has_spot)
        if len(self.region_spot_history[current_region]) > 10:
            self.region_spot_history[current_region].pop(0)
        
        if not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = 0
        
        if self.consecutive_spot_failures >= 3:
            best_region = self._find_best_region()
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.consecutive_spot_failures = 0
                if last_cluster_type != ClusterType.NONE:
                    return ClusterType.NONE
                return ClusterType.SPOT
        
        if has_spot:
            self.spot_attempt_count += 1
            if last_cluster_type == ClusterType.SPOT:
                self.spot_success_count += 1
            if self.spot_attempt_count > 0:
                self.estimated_spot_prob = self.spot_success_count / self.spot_attempt_count
            
            if self.estimated_spot_prob < 0.3 and self.consecutive_spot_failures > 0:
                if remaining_time < (steps_needed + 5) * self.step_size:
                    return ClusterType.ON_DEMAND
            
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.NONE:
                return ClusterType.SPOT
            else:
                return ClusterType.SPOT
        else:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            
            best_region = self._find_best_region()
            if best_region != current_region:
                self.env.switch_region(best_region)
                if last_cluster_type != ClusterType.NONE:
                    return ClusterType.NONE
                return ClusterType.SPOT
            
            if remaining_time < (steps_needed + 3) * self.step_size:
                return ClusterType.ON_DEMAND
            
            if self.consecutive_spot_failures >= 2:
                return ClusterType.ON_DEMAND
            
            return ClusterType.NONE

    def _find_best_region(self) -> int:
        current_region = self.env.get_current_region()
        best_region = current_region
        best_score = -1
        
        for region in range(self.total_regions):
            history = self.region_spot_history[region]
            if not history:
                score = 0.5
            else:
                score = sum(1 for h in history if h) / len(history)
            
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region