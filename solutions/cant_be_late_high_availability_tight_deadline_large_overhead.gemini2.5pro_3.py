import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_slack_strategy"

    def solve(self, spec_path: str) -> "Solution":
        self.danger_slack_seconds = self.restart_overhead * 3.0

        initial_slack = self.deadline - self.task_duration
        self.comfort_slack_seconds = initial_slack / 2.0

        if self.danger_slack_seconds >= self.comfort_slack_seconds:
            self.comfort_slack_seconds = self.danger_slack_seconds * 1.2

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        effective_work_remaining = self.get_effective_work_remaining()

        if effective_work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        slack_seconds = time_to_deadline - effective_work_remaining

        if slack_seconds < self.danger_slack_seconds:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if slack_seconds < self.comfort_slack_seconds:
            return ClusterType.ON_DEMAND
        
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
