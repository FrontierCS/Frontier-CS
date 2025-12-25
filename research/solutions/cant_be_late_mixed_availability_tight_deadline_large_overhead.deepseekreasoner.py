import sys
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
from typing import List
import math

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.remaining_work = 0.0
        self.remaining_restart_overhead = 0.0
        self.safety_margin = 0.5 * 3600  # 0.5 hours in seconds

    def solve(self, spec_path: str) -> "Solution":
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update remaining work
        if self.task_done_time:
            self.remaining_work = self.task_duration - sum(self.task_done_time)
        else:
            self.remaining_work = self.task_duration

        # Update restart overhead counter
        if self.remaining_restart_overhead > 0:
            self.remaining_restart_overhead -= self.env.gap_seconds
            if self.remaining_restart_overhead < 0:
                self.remaining_restart_overhead = 0

        # Check for interruption
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.remaining_restart_overhead = self.restart_overhead

        # If in restart overhead, wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE

        # Calculate remaining time
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # If no time left or work done, stop
        if remaining_time <= 0 or self.remaining_work <= 0:
            return ClusterType.NONE

        # Calculate effective remaining time considering restart overhead
        effective_remaining_time = remaining_time - self.restart_overhead

        # Calculate time needed if we use on-demand continuously
        time_needed_on_demand = self.remaining_work

        # Calculate time needed if we use spot (with some risk)
        time_needed_spot = self.remaining_work + self.restart_overhead * 0.5  # Conservative estimate

        # Critical condition: must use on-demand to meet deadline
        if effective_remaining_time <= time_needed_on_demand + self.safety_margin:
            return ClusterType.ON_DEMAND

        # If spot is available and we have time buffer, use spot
        if has_spot and effective_remaining_time > time_needed_spot + self.safety_margin:
            return ClusterType.SPOT

        # Otherwise use on-demand conservatively
        return ClusterType.ON_DEMAND