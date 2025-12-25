import argparse
from typing import List
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.safety_margin = 1800  # 30 minutes in seconds
        self.aggressiveness = 0.85
        self.min_slack_ratio = 0.05

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND

        # Calculate required completion rate
        required_rate = remaining_work / remaining_time if remaining_time > 0 else float('inf')
        
        # Dynamic safety margin based on remaining work
        dynamic_margin = max(self.restart_overhead * 3, 
                           min(self.safety_margin, remaining_work * 0.1))
        
        # Conservative spot usage when close to deadline
        if remaining_work > remaining_time - dynamic_margin:
            return ClusterType.ON_DEMAND
        
        # Aggressive spot usage when we have plenty of time
        if has_spot and remaining_time > self.task_duration * 1.3:
            return ClusterType.SPOT
        
        # Adaptive threshold based on progress
        progress_ratio = sum(self.task_done_time) / self.task_duration
        time_ratio = elapsed / self.deadline
        
        # Use spot if we're ahead of schedule or spot is available with good margin
        if has_spot:
            if progress_ratio > time_ratio * self.aggressiveness:
                return ClusterType.SPOT
            elif remaining_time > remaining_work * 1.5:
                return ClusterType.SPOT
        
        # Use on-demand if we're falling behind
        if progress_ratio < time_ratio - self.min_slack_ratio:
            return ClusterType.ON_DEMAND
        
        # Default to waiting if spot unavailable and we have slack
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)