import json
from argparse import Namespace
from enum import Enum
import heapq
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class State(Enum):
    INIT = 0
    SPOT_RUNNING = 1
    ON_DEMAND_RUNNING = 2
    OVERHEAD = 3


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
        
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.gap_hours = self.env.gap_seconds / 3600.0
        self.required_work_hours = self.task_duration[0] / 3600.0
        self.overhead_hours = self.restart_overhead[0] / 3600.0
        
        self.work_done_hours = 0.0
        self.current_state = State.INIT
        self.current_region = 0
        self.region_spot_history = {}
        self.time_elapsed_hours = 0.0
        
        return self

    def _update_state(self):
        self.work_done_hours = sum(self.task_done_time) / 3600.0
        self.time_elapsed_hours = self.env.elapsed_seconds / 3600.0
        self.current_region = self.env.get_current_region()
        
        if self.current_region not in self.region_spot_history:
            self.region_spot_history[self.current_region] = []
        
        if self.env.cluster_type == ClusterType.SPOT:
            self.current_state = State.SPOT_RUNNING
        elif self.env.cluster_type == ClusterType.ON_DEMAND:
            self.current_state = State.ON_DEMAND_RUNNING
        elif self.remaining_restart_overhead > 0:
            self.current_state = State.OVERHEAD
        else:
            self.current_state = State.INIT

    def _get_best_spot_region(self, has_spot_current: bool) -> int:
        num_regions = self.env.get_num_regions()
        best_region = self.current_region
        best_score = -1
        
        for region in range(num_regions):
            if region == self.current_region:
                score = 1 if has_spot_current else 0
            else:
                history = self.region_spot_history.get(region, [])
                if len(history) > 0:
                    score = sum(history) / len(history)
                else:
                    score = 0.5
            
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region

    def _should_switch_to_ondemand(self, has_spot: bool) -> bool:
        remaining_work = self.required_work_hours - self.work_done_hours
        remaining_time = (self.deadline - self.env.elapsed_seconds) / 3600.0
        
        if remaining_time <= 0:
            return True
        
        time_per_work_hour = self.gap_hours
        if not has_spot:
            time_per_work_hour += self.overhead_hours
        
        estimated_time_needed = remaining_work * time_per_work_hour
        safety_margin = self.overhead_hours * 2
        
        return (estimated_time_needed + safety_margin) > remaining_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_state()
        
        self.region_spot_history[self.current_region].append(1 if has_spot else 0)
        if len(self.region_spot_history[self.current_region]) > 10:
            self.region_spot_history[self.current_region].pop(0)
        
        remaining_work = self.required_work_hours - self.work_done_hours
        remaining_time = (self.deadline - self.env.elapsed_seconds) / 3600.0
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND
        
        if self._should_switch_to_ondemand(has_spot):
            if last_cluster_type != ClusterType.ON_DEMAND:
                best_spot_region = self._get_best_spot_region(has_spot)
                if best_spot_region != self.current_region:
                    self.env.switch_region(best_spot_region)
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if last_cluster_type != ClusterType.SPOT:
                best_spot_region = self._get_best_spot_region(has_spot)
                if best_spot_region != self.current_region:
                    self.env.switch_region(best_spot_region)
            return ClusterType.SPOT
        else:
            best_spot_region = self._get_best_spot_region(has_spot)
            if best_spot_region != self.current_region:
                self.env.switch_region(best_spot_region)
                return ClusterType.SPOT
            else:
                return ClusterType.NONE