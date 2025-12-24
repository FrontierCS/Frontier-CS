import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    K_CRITICAL_MARGIN = 1.1
    RESERVE_SLACK_FRAC = 1.0 / 3.0

    def solve(self, spec_path: str) -> "Solution":
        initial_slack = self.deadline - self.task_duration

        self.T_critical = self.restart_overhead * self.K_CRITICAL_MARGIN

        safe_slack = max(0.0, initial_slack - self.T_critical)

        self.T_wait = self.T_critical + safe_slack * self.RESERVE_SLACK_FRAC

        self._work_done_cache = 0.0
        self._processed_len = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_len = len(self.task_done_time)
        if current_len > self._processed_len:
            new_work = sum(self.task_done_time[self._processed_len:])
            self._work_done_cache += new_work
            self._processed_len = current_len

        work_remaining = self.task_duration - self._work_done_cache

        if work_remaining <= 0:
            return ClusterType.NONE

        time_remaining = self.deadline - self.env.elapsed_seconds
        slack = time_remaining - work_remaining

        if has_spot:
            if slack > self.T_critical:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            if slack > self.T_wait:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
