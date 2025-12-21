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
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.spot_available_history = []
        self.last_spot_decision = False
        self.safety_margin_factor = 1.2
        self.min_spot_prob_threshold = 0.3
        self.consecutive_spot_needed = 0
        self.last_work_rate = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _estimate_spot_availability_probability(self, recent_window: int = 100) -> float:
        if not self.spot_available_history:
            return 0.5
        
        window = min(recent_window, len(self.spot_available_history))
        recent = self.spot_available_history[-window:]
        return sum(recent) / window

    def _calculate_required_progress_rate(self) -> float:
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_time <= 0:
            return float('inf')
        return remaining_work / remaining_time

    def _calculate_conservative_required_rate(self) -> float:
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds - self.restart_overhead * 2
        if remaining_time <= 0:
            return float('inf')
        return remaining_work / remaining_time

    def _calculate_time_safety_factor(self) -> float:
        elapsed = self.env.elapsed_seconds
        total_time = self.deadline
        progress = sum(self.task_done_time) / self.task_duration if self.task_duration > 0 else 0
        
        if progress >= 1.0:
            return 2.0
        
        expected_progress = elapsed / total_time
        if expected_progress <= 0:
            return 1.0
        
        progress_ratio = progress / expected_progress if expected_progress > 0 else 1.0
        safety = 1.0 + (1.0 - progress_ratio) * 2.0
        return max(1.0, min(3.0, safety))

    def _should_switch_to_ondemand(self, spot_prob: float, required_rate: float) -> bool:
        if required_rate > 0.95:
            return True
        
        time_safety = self._calculate_time_safety_factor()
        conservative_rate = self._calculate_conservative_required_rate()
        
        if conservative_rate > 0.8:
            return True
        
        if spot_prob < self.min_spot_prob_threshold:
            threshold_adjusted = self.min_spot_prob_threshold / time_safety
            if spot_prob < threshold_adjusted:
                return True
        
        remaining_time = self.deadline - self.env.elapsed_seconds
        remaining_work = self.task_duration - sum(self.task_done_time)
        
        if remaining_time <= 0:
            return False
        
        time_needed_ondemand = remaining_work + self.restart_overhead
        time_needed_spot = remaining_work / max(spot_prob, 0.01) + self.restart_overhead * 2
        
        return time_needed_spot > remaining_time * 0.9 and time_needed_ondemand <= remaining_time * 0.95

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.spot_available_history.append(has_spot)
        if len(self.spot_available_history) > 1000:
            self.spot_available_history.pop(0)
        
        required_rate = self._calculate_required_progress_rate()
        spot_prob = self._estimate_spot_availability_probability()
        
        if last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_needed = max(0, self.consecutive_spot_needed - 1)
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.consecutive_spot_needed = 0
        
        if required_rate > 0.99:
            return ClusterType.ON_DEMAND
        
        if not has_spot:
            if required_rate > 0.7:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        if self._should_switch_to_ondemand(spot_prob, required_rate):
            return ClusterType.ON_DEMAND
        
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        if remaining_time > remaining_work * 1.5:
            if spot_prob > 0.6:
                return ClusterType.SPOT
            elif spot_prob > 0.3 and remaining_time > remaining_work * 2:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
