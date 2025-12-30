import math
import random
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self.spot_price = 0.97
        self.od_price = 3.06
        self.price_ratio = self.od_price / self.spot_price
        self.restart_hours = 0.20
        self.task_hours = 48
        self.deadline_hours = 70
        self.slack_hours = 22
        self.safety_margin = 0.1
        self.consecutive_spot_failures = 0
        self.spot_availability_history = []
        self.last_decision = ClusterType.NONE
        self.consecutive_spot_runs = 0
        self.spot_success_streak = 0
        self.work_done = 0.0
        self.time_used = 0.0
        self.expected_spot_availability = 0.22
        self.alpha = 0.1
        self.min_spot_prob = 0.04
        self.max_spot_prob = 0.40
        self.critical_threshold = 0.3
        self.aggressiveness = 1.0
        self.restart_pending = False
        self.restart_remaining = 0.0
        self.phase = "early"
        self.spot_window_size = 10
        self.recent_spot_available = []

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_spot_availability_estimate(self, has_spot: bool):
        self.recent_spot_available.append(1 if has_spot else 0)
        if len(self.recent_spot_available) > self.spot_window_size:
            self.recent_spot_available.pop(0)
        
        if len(self.recent_spot_available) > 0:
            recent_availability = sum(self.recent_spot_available) / len(self.recent_spot_available)
            self.expected_spot_availability = (1 - self.alpha) * self.expected_spot_availability + self.alpha * recent_availability
            self.expected_spot_availability = max(self.min_spot_prob, min(self.max_spot_prob, self.expected_spot_availability))

    def _calculate_risk_factor(self) -> float:
        remaining_work = max(0.0, self.task_duration - self.work_done)
        remaining_time = max(0.0, self.deadline - self.env.elapsed_seconds)
        
        if remaining_time <= 0 or remaining_work <= 0:
            return 1.0
        
        hours_remaining = remaining_time / 3600
        work_hours_needed = remaining_work / 3600
        
        baseline_time = work_hours_needed / 0.9
        time_risk = max(0.0, baseline_time - hours_remaining) / (self.slack_hours + 1e-6)
        
        progress_ratio = self.work_done / max(1.0, self.task_duration)
        time_ratio = self.env.elapsed_seconds / max(1.0, self.deadline)
        schedule_risk = max(0.0, time_ratio - progress_ratio)
        
        combined_risk = min(1.0, time_risk * 0.7 + schedule_risk * 0.3)
        
        if hours_remaining < work_hours_needed * (1 + self.restart_hours):
            combined_risk = 1.0
            
        return combined_risk

    def _should_use_spot(self, has_spot: bool, risk_factor: float) -> bool:
        if not has_spot:
            return False
            
        if risk_factor > self.critical_threshold:
            return False
            
        if self.consecutive_spot_failures > 2:
            if random.random() < 0.3:
                return False
                
        spot_prob = max(0.1, 1.0 - risk_factor * self.aggressiveness)
        
        if self.expected_spot_availability < 0.1:
            spot_prob *= 0.5
            
        if self.consecutive_spot_runs > 5:
            spot_prob *= 0.8
            
        return random.random() < spot_prob

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_spot_availability_estimate(has_spot)
        
        time_step_hours = self.env.gap_seconds / 3600
        risk_factor = self._calculate_risk_factor()
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
            self.consecutive_spot_runs = 0
            self.spot_success_streak = 0
        elif last_cluster_type == ClusterType.SPOT and has_spot:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
            self.consecutive_spot_runs += 1
            self.spot_success_streak += 1
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 2)
            self.consecutive_spot_runs = 0
        else:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
            
        remaining_work = max(0.0, self.task_duration - self.work_done)
        remaining_time = max(0.0, self.deadline - self.env.elapsed_seconds)
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND
            
        hours_remaining = remaining_time / 3600
        work_hours_needed = remaining_work / 3600
        
        if hours_remaining < work_hours_needed * 1.05:
            return ClusterType.ON_DEMAND
            
        if risk_factor > 0.8:
            return ClusterType.ON_DEMAND
            
        if self._should_use_spot(has_spot, risk_factor):
            if has_spot:
                return ClusterType.SPOT
            elif risk_factor < 0.5:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
        else:
            if risk_factor > 0.6:
                return ClusterType.ON_DEMAND
            elif risk_factor < 0.2 and not has_spot:
                return ClusterType.NONE
            elif has_spot and self.expected_spot_availability > 0.3:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)