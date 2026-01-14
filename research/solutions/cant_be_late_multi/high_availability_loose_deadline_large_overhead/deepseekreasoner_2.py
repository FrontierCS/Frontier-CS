import json
from argparse import Namespace
from typing import List, Tuple
from enum import Enum
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class StrategyState(Enum):
    SPOT_HUNTING = 1
    SPOT_RUNNING = 2
    ON_DEMAND = 3
    FINISHING = 4


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

    def __init__(self, args):
        super().__init__(args)
        self.region_count = 0
        self.spot_history = {}
        self.current_region = 0
        self.state = StrategyState.SPOT_HUNTING
        self.consecutive_spot_failures = 0
        self.last_work_region = -1
        self.region_reliability = {}
        self.time_in_region = {}
        self.switch_counter = 0
        self.spot_streak = 0
        self.max_switch_before_giveup = 3
        self.critical_time_threshold = 0.8

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

    def _update_region_stats(self, region_idx: int, had_spot: bool):
        if region_idx not in self.spot_history:
            self.spot_history[region_idx] = []
            self.time_in_region[region_idx] = 0
            self.region_reliability[region_idx] = 0.5
        
        self.spot_history[region_idx].append(1 if had_spot else 0)
        if len(self.spot_history[region_idx]) > 10:
            self.spot_history[region_idx].pop(0)
        
        reliability = sum(self.spot_history[region_idx]) / len(self.spot_history[region_idx])
        self.region_reliability[region_idx] = reliability

    def _get_best_spot_region(self) -> int:
        best_region = self.current_region
        best_score = -1
        
        for region in range(self.env.get_num_regions()):
            if region == self.current_region:
                continue
                
            reliability = self.region_reliability.get(region, 0.5)
            time_in_region_val = self.time_in_region.get(region, 0)
            
            score = reliability * (1 + 0.1 * time_in_region_val)
            
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region

    def _should_switch_to_on_demand(self) -> bool:
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        if remaining_time <= 0:
            return True
            
        time_per_work_unit = remaining_time / remaining_work if remaining_work > 0 else float('inf')
        
        safe_threshold = self.restart_overhead * 3
        
        if remaining_time < safe_threshold:
            return True
            
        if remaining_work > 0 and time_per_work_unit < self.restart_overhead * 2:
            return True
            
        if self.consecutive_spot_failures >= self.max_switch_before_giveup:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.current_region = self.env.get_current_region()
        self._update_region_stats(self.current_region, has_spot)
        self.time_in_region[self.current_region] = self.time_in_region.get(self.current_region, 0) + 1
        
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        if remaining_work <= 0 or remaining_time <= 0:
            return ClusterType.NONE
            
        if self._should_switch_to_on_demand():
            self.state = StrategyState.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        time_fraction = self.env.elapsed_seconds / self.deadline
        
        if time_fraction > self.critical_time_threshold and remaining_work > 0:
            self.state = StrategyState.FINISHING
            if has_spot and self.spot_streak > 2:
                self.spot_streak += 1
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        if self.state == StrategyState.SPOT_HUNTING:
            if has_spot:
                self.state = StrategyState.SPOT_RUNNING
                self.spot_streak = 1
                self.consecutive_spot_failures = 0
                return ClusterType.SPOT
            else:
                best_region = self._get_best_spot_region()
                if best_region != self.current_region:
                    self.env.switch_region(best_region)
                    self.switch_counter += 1
                    self.consecutive_spot_failures += 1
                return ClusterType.NONE
        
        elif self.state == StrategyState.SPOT_RUNNING:
            if has_spot:
                self.spot_streak += 1
                self.consecutive_spot_failures = 0
                if self.spot_streak >= 5:
                    self.last_work_region = self.current_region
                return ClusterType.SPOT
            else:
                self.state = StrategyState.SPOT_HUNTING
                self.consecutive_spot_failures += 1
                
                if self.consecutive_spot_failures <= 2 and self.last_work_region != -1:
                    if self.last_work_region != self.current_region:
                        self.env.switch_region(self.last_work_region)
                        self.switch_counter += 1
                
                if self.consecutive_spot_failures > 1:
                    best_region = self._get_best_spot_region()
                    if best_region != self.current_region:
                        self.env.switch_region(best_region)
                        self.switch_counter += 1
                
                return ClusterType.NONE
        
        elif self.state == StrategyState.ON_DEMAND:
            if remaining_time > self.restart_overhead * 4 and remaining_work > self.env.gap_seconds * 2:
                if has_spot and self.consecutive_spot_failures < 2:
                    self.state = StrategyState.SPOT_RUNNING
                    self.spot_streak = 1
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        return ClusterType.NONE