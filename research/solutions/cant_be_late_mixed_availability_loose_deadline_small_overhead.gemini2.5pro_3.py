import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "risk_aware_slack_manager"

    def solve(self, spec_path: str) -> "Solution":
        self.P_SPOT_INIT = 0.5
        self.ALPHA_UP = 0.05
        self.ALPHA_DOWN = 0.20
        self.SAFETY_THRESHOLD_FACTOR = 2.0
        self.P_SPOT_MIN_THRESHOLD = 0.01

        self.p_spot_avail = self.P_SPOT_INIT
        self.work_done_cache = 0.0
        self.last_task_done_len = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if has_spot:
            alpha = self.ALPHA_UP
            spot_val = 1.0
        else:
            alpha = self.ALPHA_DOWN
            spot_val = 0.0
        self.p_spot_avail = alpha * spot_val + (1 - alpha) * self.p_spot_avail

        current_len = len(self.task_done_time)
        if current_len > self.last_task_done_len:
            if self.last_task_done_len == 0:
                self.work_done_cache = sum(end - start for start, end in self.task_done_time)
            else:
                new_segments = self.task_done_time[self.last_task_done_len:]
                self.work_done_cache += sum(end - start for start, end in new_segments)
            self.last_task_done_len = current_len

        work_remaining = self.task_duration - self.work_done_cache

        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_to_deadline - work_remaining

        if current_slack <= self.env.gap_seconds:
            return ClusterType.ON_DEMAND

        if has_spot:
            risk_threshold = self.restart_overhead * self.SAFETY_THRESHOLD_FACTOR
            if current_slack < risk_threshold:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT
        else:
            if self.p_spot_avail < self.P_SPOT_MIN_THRESHOLD:
                return ClusterType.ON_DEMAND

            expected_wait_time = (1.0 / self.p_spot_avail - 1.0) * self.env.gap_seconds

            if current_slack > expected_wait_time:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: "argparse.ArgumentParser") -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)