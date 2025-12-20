import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_slack"

    MIN_COMFORTABLE_SLACK_PCT = 0.25
    MAX_COMFORTABLE_SLACK_PCT = 0.80

    def __init__(self, args):
        super().__init__(args)
        self._initialized = False
        self.critical_slack_threshold = 0.0
        self.min_comfortable_threshold = 0.0
        self.max_comfortable_threshold = 0.0
        self.spot_seen_available = 0
        self.total_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_strategy(self):
        if self._initialized:
            return

        self.critical_slack_threshold = self.restart_overhead + self.env.gap_seconds

        initial_slack = self.deadline - self.task_duration
        
        if initial_slack <= self.critical_slack_threshold:
            initial_slack = self.critical_slack_threshold * 5.0

        min_thresh = initial_slack * self.MIN_COMFORTABLE_SLACK_PCT
        max_thresh = initial_slack * self.MAX_COMFORTABLE_SLACK_PCT
        
        self.min_comfortable_threshold = max(min_thresh, self.critical_slack_threshold * 1.1)
        self.max_comfortable_threshold = max(max_thresh, self.min_comfortable_threshold * 1.1)

        self._initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_strategy()

        self.total_steps += 1
        if has_spot:
            self.spot_seen_available += 1

        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_left_to_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_left_to_deadline - work_remaining

        if current_slack < self.critical_slack_threshold:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self.total_steps > 0:
            availability_estimate = self.spot_seen_available / self.total_steps
        else:
            availability_estimate = 0.5

        comfortable_slack_threshold = self.max_comfortable_threshold - \
            (availability_estimate * (self.max_comfortable_threshold - self.min_comfortable_threshold))

        if current_slack > comfortable_slack_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)
