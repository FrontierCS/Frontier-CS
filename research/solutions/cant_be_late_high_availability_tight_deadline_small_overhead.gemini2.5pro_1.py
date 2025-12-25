import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Total initial slack is deadline (52h) - task_duration (48h) = 4 hours.
        # We partition this 4-hour slack into decision zones.

        # Enter CAUTION zone when slack drops below this value (2 hours).
        self.CAUTION_SLACK_SECONDS = 2.0 * 3600

        # Enter DANGER zone when slack drops below this value (30 minutes).
        self.DANGER_SLACK_SECONDS = 0.5 * 3600
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Calculate work remaining.
        work_done_seconds = sum(end - start for start, end in self.task_done_time)
        work_remaining_seconds = self.task_duration - work_done_seconds

        # If the job is finished, do nothing.
        if work_remaining_seconds <= 0:
            return ClusterType.NONE

        # 2. Calculate current slack.
        # Slack is the time we can be idle and still finish by the deadline
        # using on-demand instances for all remaining work.
        time_now = self.env.elapsed_seconds
        time_to_deadline = self.deadline - time_now
        
        # As a safeguard, if we're past the deadline, try to finish.
        if time_to_deadline <= 0:
            return ClusterType.ON_DEMAND

        slack_seconds = time_to_deadline - work_remaining_seconds

        # 3. Make a decision based on the current slack zone.
        if slack_seconds < self.DANGER_SLACK_SECONDS:
            # Danger Zone: Critically low on time. Must use On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND
        
        elif slack_seconds < self.CAUTION_SLACK_SECONDS:
            # Caution Zone: Time is getting tight. Can't afford to wait.
            # Use SPOT if available for cost savings, but fall back to ON_DEMAND
            # to ensure continuous progress.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        else:
            # Safe Zone: Plenty of slack. Prioritize maximum cost savings.
            # Use SPOT or wait if it's unavailable.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        # Required method for evaluator instantiation.
        args, _ = parser.parse_known_args()
        return cls(args)