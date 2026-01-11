import json
from argparse import Namespace
import math
from enum import Enum

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class State(Enum):
    SPOT_SEARCHING = 1
    SPOT_RUNNING = 2
    ONDEMAND_GUARANTEE = 3
    FINISHING = 4


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
        
        self.region_visits = {}
        self.current_state = State.SPOT_SEARCHING
        self.spot_streak = 0
        self.consecutive_spot_failures = 0
        self.last_region_switch_time = 0
        self.min_spot_streak_before_switch = 3
        self.emergency_ondemand_threshold = 0.15
        
        return self

    def _get_remaining_work(self):
        return max(0.0, self.task_duration[0] - sum(self.task_done_time))

    def _get_time_remaining(self):
        return max(0.0, self.deadline - self.env.elapsed_seconds)

    def _get_safe_time_needed(self):
        remaining_work = self._get_remaining_work()
        return remaining_work + self.restart_overhead[0]

    def _is_critical_time(self):
        time_remaining = self._get_time_remaining()
        safe_needed = self._get_safe_time_needed()
        return time_remaining < safe_needed * (1.0 + self.emergency_ondemand_threshold)

    def _should_switch_region_for_spot(self, has_spot):
        if not has_spot:
            if self.consecutive_spot_failures >= 2:
                return True
            
            current_region = self.env.get_current_region()
            time_since_last_switch = self.env.elapsed_seconds - self.last_region_switch_time
            
            if time_since_last_switch > self.restart_overhead[0] * 5:
                return True
        return False

    def _find_best_region_for_spot(self, current_region, has_spot):
        num_regions = self.env.get_num_regions()
        
        if has_spot:
            return current_region
        
        best_region = current_region
        best_score = -float('inf')
        
        for region in range(num_regions):
            if region == current_region:
                continue
                
            visits = self.region_visits.get(region, 0)
            score = 1.0 / (visits + 1)
            
            if score > best_score:
                best_score = score
                best_region = region
        
        self.region_visits[best_region] = self.region_visits.get(best_region, 0) + 1
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self._get_remaining_work()
        time_remaining = self._get_time_remaining()
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        if time_remaining <= 0:
            return ClusterType.ON_DEMAND
        
        current_region = self.env.get_current_region()
        
        if self._is_critical_time():
            self.current_state = State.FINISHING
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        if self.current_state == State.FINISHING:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        if self._should_switch_region_for_spot(has_spot):
            best_region = self._find_best_region_for_spot(current_region, has_spot)
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.last_region_switch_time = self.env.elapsed_seconds
                self.consecutive_spot_failures = 0
                self.spot_streak = 0
                return ClusterType.NONE
        
        if has_spot:
            self.consecutive_spot_failures = 0
            
            if self.current_state == State.SPOT_SEARCHING:
                self.current_state = State.SPOT_RUNNING
                self.spot_streak = 1
                return ClusterType.SPOT
            
            elif self.current_state == State.SPOT_RUNNING:
                self.spot_streak += 1
                
                required_spot_streak = max(2, int(self.restart_overhead[0] / 3600) * 2)
                if self.spot_streak >= required_spot_streak:
                    safe_needed = self._get_safe_time_needed()
                    time_needed_if_fail = safe_needed + self.restart_overhead[0]
                    
                    if time_remaining < time_needed_if_fail * 1.2:
                        self.current_state = State.ONDEMAND_GUARANTEE
                        return ClusterType.ON_DEMAND
                
                return ClusterType.SPOT
            
            elif self.current_state == State.ONDEMAND_GUARANTEE:
                if self.spot_streak >= self.min_spot_streak_before_switch:
                    self.current_state = State.SPOT_RUNNING
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        
        else:
            self.consecutive_spot_failures += 1
            self.spot_streak = 0
            
            if self.current_state == State.SPOT_RUNNING:
                if self.consecutive_spot_failures >= 2:
                    self.current_state = State.ONDEMAND_GUARANTEE
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.NONE
            
            elif self.current_state == State.SPOT_SEARCHING:
                return ClusterType.NONE
            
            elif self.current_state == State.ONDEMAND_GUARANTEE:
                return ClusterType.ON_DEMAND
        
        return ClusterType.NONE