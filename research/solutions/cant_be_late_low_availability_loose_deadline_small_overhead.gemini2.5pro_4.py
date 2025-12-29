import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy parameters based on the problem specification.
        This sets up two slack-based thresholds that govern the strategy's
        decision-making process.
        """
        initial_slack = self.deadline - self.task_duration

        if initial_slack > 0:
            # Ratio of remaining slack at which we stop waiting for Spot and
            # start using On-Demand to guarantee progress. A higher value
            # is more conservative.
            wait_slack_ratio = 0.60

            # Ratio of remaining slack that triggers "panic mode", where we
            # use On-Demand exclusively. This is a final safety buffer.
            panic_slack_ratio = 0.20

            self.WAIT_SLACK = initial_slack * wait_slack_ratio
            self.PANIC_SLACK = initial_slack * panic_slack_ratio
        else:
            # If there's no initial slack, we must be conservative from the start.
            self.WAIT_SLACK = 0
            self.PANIC_SLACK = 0
            
        return self

    def _get_work_done(self) -> float:
        """Helper to calculate total work completed."""
        return sum(self.task_done_time)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Core decision logic, called at each time step.
        """
        work_done = self._get_work_done()
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # Desperation check: if remaining work exceeds time to deadline,
        # we are projected to fail. On-Demand is the only option.
        if time_to_deadline <= work_remaining:
            return ClusterType.ON_DEMAND

        current_slack = time_to_deadline - work_remaining

        # Panic mode: if slack is below the critical threshold, use On-Demand
        # exclusively to ensure completion.
        if current_slack <= self.PANIC_SLACK:
            return ClusterType.ON_DEMAND

        # Main logic: choose based on spot availability and slack.
        if has_spot:
            # Spot is available, always choose it for cost savings.
            return ClusterType.SPOT
        else:
            # Spot is unavailable. Decide whether to use On-Demand or wait.
            if current_slack <= self.WAIT_SLACK:
                # Slack is no longer abundant. Use On-Demand to preserve the
                # remaining slack and make progress.
                return ClusterType.ON_DEMAND
            else:
                # Slack is plentiful. We can afford to wait for Spot to become
                # available again, saving costs.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """Required method for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)