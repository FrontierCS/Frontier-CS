import json
import math
from enum import Enum
from typing import List, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__()
        self.args = args
        self.spec = {}
        self.critical_threshold = 0.0
        self.spot_history = []
        self.window_size = 100
        self.spot_availability = 0.5
        self.min_spot_availability = 0.05
        self.restart_penalty_factor = 2.0
        self.conservative_factor = 1.2
        self.last_action = ClusterType.NONE
        self.spot_streak = 0
        self.od_streak = 0
        self.panic_mode = False
        self.required_rate = 0.0
        self.safety_margin = 0.0

    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                self.spec = json.load(f)
        except:
            pass
        return self

    def _compute_required_rate(self) -> float:
        elapsed = self.env.elapsed_seconds
        remaining_time = max(0.0, self.deadline - elapsed)
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        work_remaining = max(0.0, self.task_duration - work_done)
        
        if remaining_time <= 0:
            return float('inf')
        
        required = work_remaining / remaining_time
        self.required_rate = required
        return required

    def _update_spot_history(self, has_spot: bool):
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > self.window_size:
            self.spot_history.pop(0)
        
        if len(self.spot_history) > 0:
            self.spot_availability = sum(self.spot_history) / len(self.spot_history)
        else:
            self.spot_availability = self.min_spot_availability

    def _should_use_spot(self, has_spot: bool) -> bool:
        if not has_spot:
            return False
            
        required_rate = self._compute_required_rate()
        elapsed = self.env.elapsed_seconds
        remaining_time = max(0.0, self.deadline - elapsed)
        
        if remaining_time < self.restart_overhead * self.restart_penalty_factor:
            return False
            
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        work_remaining = max(0.0, self.task_duration - work_done)
        
        expected_spot_rate = self.spot_availability * (1.0 - self.restart_overhead / (self.gap_seconds * 10))
        required_with_safety = required_rate * self.conservative_factor
        
        if expected_spot_rate >= required_with_safety and self.spot_availability > self.min_spot_availability:
            return True
            
        time_needed_spot = work_remaining / max(0.01, expected_spot_rate)
        time_needed_od = work_remaining
        
        if time_needed_spot * 0.97 + self.restart_overhead * 2 < time_needed_od:
            return True
            
        return False

    def _should_use_ondemand(self) -> bool:
        required_rate = self._compute_required_rate()
        elapsed = self.env.elapsed_seconds
        remaining_time = max(0.0, self.deadline - elapsed)
        
        if remaining_time <= 0:
            return True
            
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        work_remaining = max(0.0, self.task_duration - work_done)
        
        time_needed_od = work_remaining
        critical_threshold = self.restart_overhead * 3
        
        if remaining_time - time_needed_od < critical_threshold:
            return True
            
        if required_rate > 0.8:
            return True
            
        if self.panic_mode:
            return True
            
        expected_spot_success = self.spot_availability
        if expected_spot_success < 0.3 and required_rate > 0.5:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_spot_history(has_spot)
        required_rate = self._compute_required_rate()
        
        elapsed = self.env.elapsed_seconds
        remaining_time = max(0.0, self.deadline - elapsed)
        
        if remaining_time <= 0:
            return ClusterType.NONE
            
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        work_remaining = max(0.0, self.task_duration - work_done)
        
        if work_remaining <= 0:
            return ClusterType.NONE
            
        if last_cluster_type == ClusterType.SPOT:
            self.spot_streak += 1
            self.od_streak = 0
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.od_streak += 1
            self.spot_streak = 0
        else:
            self.spot_streak = max(0, self.spot_streak - 1)
            self.od_streak = max(0, self.od_streak - 1)
        
        self.last_action = last_cluster_type
        
        if self._should_use_ondemand():
            self.panic_mode = remaining_time < self.task_duration * 0.7
            return ClusterType.ON_DEMAND
            
        if self._should_use_spot(has_spot):
            if has_spot:
                return ClusterType.SPOT
            else:
                if remaining_time < work_remaining * 1.1:
                    return ClusterType.ON_DEMAND
                return ClusterType.NONE
        else:
            if has_spot and self.spot_streak > 5:
                return ClusterType.SPOT
            
            if remaining_time > work_remaining * 1.5:
                return ClusterType.NONE
            else:
                if has_spot:
                    return ClusterType.SPOT
                else:
                    if remaining_time < work_remaining * 1.2:
                        return ClusterType.ON_DEMAND
                    return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)