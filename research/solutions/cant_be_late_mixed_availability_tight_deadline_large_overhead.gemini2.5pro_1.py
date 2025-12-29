import argparse
from collections import deque

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    SPOT_HISTORY_WINDOW = 360
    BUFFER_MULTIPLIER_MAX = 3.0
    BUFFER_MULTIPLIER_MIN = 1.25

    def solve(self, spec_path: str) -> "Solution":
        self.pending_overhead = 0.0
        self.work_done_cache = 0.0
        self.last_num_segments = 0
        self.spot_history = deque(maxlen=self.SPOT_HISTORY_WINDOW)
        self.steps_observed = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.steps_observed += 1
        self.spot_history.append(1 if has_spot else 0)

        preempted = (last_cluster_type == ClusterType.SPOT and
                     self.env.cluster_type == ClusterType.NONE)
        if preempted:
            self.pending_overhead = self.restart_overhead
        elif last_cluster_type in [ClusterType.SPOT, ClusterType.ON_DEMAND]:
            self.pending_overhead = max(0.0, self.pending_overhead - self.env.gap_seconds)

        if len(self.task_done_time) > self.last_num_segments:
            self.work_done_cache = sum(self.task_done_time)
            self.last_num_segments = len(self.task_done_time)

        work_remaining = self.task_duration - self.work_done_cache

        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_needed_to_run = work_remaining + self.pending_overhead
        critical_time = self.deadline - time_needed_to_run
        current_time = self.env.elapsed_seconds
        slack = critical_time - current_time

        if slack <= 0:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self.steps_observed < self.SPOT_HISTORY_WINDOW:
            recent_availability = (0.78 + 0.04) / 2
        else:
            recent_availability = sum(self.spot_history) / self.SPOT_HISTORY_WINDOW

        multiplier_range = self.BUFFER_MULTIPLIER_MAX - self.BUFFER_MULTIPLIER_MIN
        buffer_multiplier = self.BUFFER_MULTIPLIER_MAX - recent_availability * multiplier_range
        
        adaptive_buffer = self.restart_overhead * buffer_multiplier
        
        if slack < adaptive_buffer:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)