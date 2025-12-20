import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # A simple, robust strategy is to define behavior based on the
        # remaining "slack". Slack is the amount of time we can afford to
        # waste (e.g., waiting for Spot) and still meet the deadline if we
        # switch to a guaranteed On-Demand instance.
        #
        # slack = (time_to_deadline) - (work_remaining_on_on_demand)
        #
        # We define two thresholds for slack to create three operating modes:
        # 1. Normal Mode (high slack): Prioritize cost. Use Spot if available,
        #    otherwise wait (NONE).
        # 2. Cautious Mode (low slack): Prioritize progress. Use Spot if
        #    available, but use On-Demand if not. Don't wait.
        # 3. Critical Mode (very low slack): Prioritize deadline. Use On-Demand
        #    unconditionally to guarantee completion.
        #
        # Thresholds are tuned based on the restart_overhead, which is the
        # primary penalty for using Spot.
        # restart_overhead = 0.20 hours = 720 seconds.
        # total_slack = 4 hours = 14400 seconds.

        # Critical Threshold: set to 1.5x the overhead. If slack is less than
        # this, a single preemption could cause us to miss the deadline.
        # 1.5 * 720s = 1080s (18 minutes)
        self.CRITICAL_SLACK_THRESHOLD = 1.5 * self.restart_overhead

        # Cautious Threshold: set to 5x the overhead. This means we start
        # being cautious when our slack drops to 3600s (1 hour), having
        # used up ~75% of our initial slack.
        self.CAUTIOUS_SLACK_THRESHOLD = 5.0 * self.restart_overhead

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # 1. Calculate current progress and remaining work.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_rem = self.task_duration - work_done

        # If the job is complete, do nothing to avoid unnecessary costs.
        if work_rem <= 0:
            return ClusterType.NONE

        # 2. Calculate current slack.
        # This is the key metric for our decision-making.
        time_needed_on_demand = work_rem
        time_until_deadline = self.deadline - self.env.elapsed_seconds
        slack = time_until_deadline - time_needed_on_demand

        # 3. Apply the slack-based, three-mode policy.

        # Critical Mode: Slack is dangerously low.
        if slack < self.CRITICAL_SLACK_THRESHOLD:
            return ClusterType.ON_DEMAND

        # Cautious Mode: Slack is low, prioritize making progress.
        elif slack < self.CAUTIOUS_SLACK_THRESHOLD:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # Normal Mode: Plenty of slack, prioritize saving cost.
        else: # slack >= self.CAUTIOUS_SLACK_THRESHOLD
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """REQUIRED: For evaluator instantiation"""
        args, _ = parser.parse_known_args()
        return cls(args)
