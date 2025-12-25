from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    A strategy for the Cant-Be-Late Scheduling Problem that aims to minimize
    cost by prioritizing Spot instances while ensuring the job finishes before
    the deadline.

    The core of the strategy is a dynamic, slack-based heuristic:
    1.  **Panic Mode**: If the time remaining is barely enough to finish the
        job even with a guaranteed On-Demand instance, we must use On-Demand.
        This is determined by comparing the current "slack" to a small safety margin.

    2.  **Opportunistic Spot**: If Spot instances are available and we are not in
        panic mode, we always use them as they are the most cost-effective option.

    3.  **Proactive On-Demand**: If Spot is unavailable, we decide between waiting
        (no cost, but consumes slack) and using a pricey On-Demand instance
        (makes progress, preserves slack). This decision is based on the ratio
        of our current slack to the remaining work. If this ratio falls below a
        threshold, it indicates we are falling behind schedule, and we proactively
        switch to On-Demand to catch up. Otherwise, we wait.

    This approach balances cost-saving against the risk of deadline failure,
    adapting its risk-aversion as the job progresses and the time buffer shrinks.
    """
    NAME = "slack_ratio_balancer"

    # --- Hyperparameters ---

    # Safety margin for panic mode, in units of restart_overhead.
    # If slack drops below this critical threshold, we must use On-Demand.
    SAFETY_MARGIN_FACTOR = 2.0

    # Proactive On-Demand threshold.
    # If the ratio of slack to remaining work drops below this, we use
    # On-Demand instead of waiting for Spot to avoid falling too far behind.
    # The initial slack ratio for the given problem is (70-48)/48 ~= 0.458.
    # A value of 0.25 means we start getting conservative when our buffer
    # is less than 25% of the work left to be done.
    SLACK_RATIO_THRESHOLD = 0.25

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step to decide which cluster type to use next.
        """
        # Calculate the amount of work remaining.
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        # If the job is already finished, idle to save costs.
        if work_rem <= 0:
            return ClusterType.NONE

        # Calculate the current time and our time buffer ("slack").
        time_current = self.env.elapsed_seconds

        # "Slack" is defined as the buffer we have compared to a schedule
        # that runs On-Demand continuously from now until the deadline.
        # It's the latest possible time to start this continuous OD work.
        latest_od_start_time = self.deadline - work_rem
        slack = latest_od_start_time - time_current

        # --- Decision Logic ---

        # 1. Panic Mode: Is our slack critically low?
        # If we are within a small safety margin of the point of no return,
        # we have no choice but to use On-Demand to guarantee completion.
        safety_margin = self.SAFETY_MARGIN_FACTOR * self.restart_overhead
        if slack < safety_margin:
            return ClusterType.ON_DEMAND

        # 2. Opportunistic Spot: Is the cheapest option available?
        # If Spot instances are available and we are not in panic mode,
        # using them is the best choice to minimize cost.
        if has_spot:
            return ClusterType.SPOT

        # 3. Proactive On-Demand vs. Waiting (if Spot is unavailable)
        # We must choose between using expensive On-Demand to make progress
        # or waiting (NONE) for a cheap Spot instance to become available.
        # This decision is based on our slack-to-work ratio.
        current_slack_ratio = slack / work_rem

        if current_slack_ratio < self.SLACK_RATIO_THRESHOLD:
            # Our time buffer is becoming too small relative to the work left.
            # We can't afford to risk waiting and losing more slack.
            # We proactively use On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND
        else:
            # We have a healthy time buffer. It's cost-effective to wait
            # for a Spot instance to become available.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required class method for the evaluator to instantiate the solution.
        """
        args, _ = parser.parse_known_args()
        return cls(args)