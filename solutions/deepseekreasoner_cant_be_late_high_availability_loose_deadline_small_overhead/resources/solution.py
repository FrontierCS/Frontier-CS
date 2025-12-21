import argparse
import math
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.aggressive_mode = False
        self.last_decision = ClusterType.NONE
        self.consecutive_spot_failures = 0
        self.spot_availability_history = []
        self.spot_success_rate = 0.5
        self.min_confidence = 0.3
        self.safety_margin_factor = 1.2

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _calculate_progress_metrics(self) -> Tuple[float, float, float, float]:
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_left = self.deadline - elapsed
        
        if remaining_work <= 0:
            return 1.0, 0.0, time_left, elapsed
        
        progress_ratio = work_done / self.task_duration
        urgency = remaining_work / max(time_left, 1e-9)
        
        return progress_ratio, urgency, time_left, elapsed

    def _should_switch_to_ondemand(self, progress_ratio: float, urgency: float, 
                                 time_left: float, remaining_work: float) -> bool:
        if urgency > 1.0:
            return True
        
        conservative_threshold = 0.7
        if progress_ratio > conservative_threshold and urgency > 0.8:
            return True
        
        if self.aggressive_mode and urgency > 0.9:
            return True
        
        time_needed_od = remaining_work
        if self.last_decision != ClusterType.ON_DEMAND:
            time_needed_od += self.restart_overhead
        
        safety_margin = self.restart_overhead * self.safety_margin_factor
        if time_left < time_needed_od + safety_margin:
            return True
        
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if last_cluster_type != ClusterType.NONE:
            self.last_decision = last_cluster_type
        
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        if self.spot_availability_history:
            self.spot_success_rate = sum(self.spot_availability_history) / len(self.spot_availability_history)
        
        progress_ratio, urgency, time_left, elapsed = self._calculate_progress_metrics()
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        if self.last_decision == ClusterType.ON_DEMAND:
            self.consecutive_spot_failures = 0
            return ClusterType.ON_DEMAND
        
        if self._should_switch_to_ondemand(progress_ratio, urgency, time_left, remaining_work):
            self.aggressive_mode = True
            self.consecutive_spot_failures = 0
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if self.last_decision == ClusterType.SPOT:
                self.consecutive_spot_failures = 0
                return ClusterType.SPOT
            
            spot_success_prob = self.spot_success_rate
            expected_spot_time = remaining_work / spot_success_prob if spot_success_prob > 0 else float('inf')
            time_needed_od = remaining_work + (self.restart_overhead if self.last_decision != ClusterType.ON_DEMAND else 0)
            
            if expected_spot_time * 0.8 < time_needed_od and spot_success_prob > self.min_confidence:
                self.consecutive_spot_failures = 0
                return ClusterType.SPOT
        
        if not has_spot:
            self.consecutive_spot_failures += 1
            
            if self.consecutive_spot_failures > 5 and urgency > 0.5:
                self.aggressive_mode = True
                return ClusterType.ON_DEMAND
        
        if elapsed > self.deadline * 0.8 and urgency > 0.6:
            self.aggressive_mode = True
        
        if self.aggressive_mode and not has_spot and urgency > 0.4:
            return ClusterType.ON_DEMAND
        
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
