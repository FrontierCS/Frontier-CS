import argparse
import math
from typing import List, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_slack_optimizer"

    def __init__(self, args):
        super().__init__(args)
        self.spot_available_history = []
        self.spot_availability_window = 100
        self.conservative_threshold = 0.15
        self.aggressive_threshold = 0.35
        self.min_spot_streak = 3
        self.current_spot_streak = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _calculate_spot_availability(self) -> float:
        if not self.spot_available_history:
            return 0.5
        window = self.spot_available_history[-self.spot_availability_window :]
        return sum(window) / len(window)

    def _should_use_spot(self, has_spot: bool, time_remaining: float, work_remaining: float) -> bool:
        if not has_spot:
            return False

        if time_remaining <= 0 or work_remaining <= 0:
            return False

        slack_ratio = (time_remaining - work_remaining) / time_remaining if time_remaining > 0 else -1

        availability = self._calculate_spot_availability()

        if slack_ratio < self.conservative_threshold:
            return False
        elif slack_ratio < self.aggressive_threshold:
            return availability > 0.6 and self.current_spot_streak >= self.min_spot_streak
        else:
            return availability > 0.3

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.spot_available_history.append(1 if has_spot else 0)
        if len(self.spot_available_history) > 1000:
            self.spot_available_history.pop(0)

        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - work_done)

        if work_remaining <= 0:
            return ClusterType.NONE

        if time_remaining <= 0:
            return ClusterType.ON_DEMAND

        time_per_step = self.env.gap_seconds / 3600.0

        effective_work_remaining = work_remaining
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            effective_work_remaining += self.restart_overhead

        critical_time_needed = effective_work_remaining + (self.restart_overhead * 2)
        is_critical = time_remaining < critical_time_needed

        if is_critical:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.current_spot_streak += 1
        else:
            self.current_spot_streak = 0

        use_spot = self._should_use_spot(has_spot, time_remaining, work_remaining)

        if use_spot:
            return ClusterType.SPOT

        buffer_needed = work_remaining + self.restart_overhead
        if time_remaining > buffer_needed * 1.2:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
