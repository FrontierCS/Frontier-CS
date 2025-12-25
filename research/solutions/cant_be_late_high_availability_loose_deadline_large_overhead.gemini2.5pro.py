import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # This factor determines how much slack we need before we are willing
        # to wait for spot instances. A higher value means we wait more readily.
        self.wait_slack_threshold_factor = 5.0

        # This factor adds a safety margin to our "danger zone" calculation
        # to make the strategy more robust.
        self.safety_margin_factor = 1.1

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
        # 1. Calculate current progress and remaining work
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the job is finished, do nothing to minimize cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Calculate remaining time and slack
        # Slack is the buffer time we have if we were to run the rest of the
        # job on a guaranteed (On-Demand) instance.
        time_left_until_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_left_until_deadline - work_remaining

        # 3. Define thresholds based on the time cost of a preemption
        # A preemption costs the restart_overhead plus the time of the current
        # step (gap_seconds) during which no work was done.
        preemption_time_cost = self.restart_overhead + self.env.gap_seconds

        # 4. Decision Logic
        # Rule 1: Danger Zone.
        # If current slack is less than the cost of a preemption (with a safety
        # margin), we are in the "danger zone". A single preemption could cause
        # us to miss the deadline. We must use On-Demand to guarantee progress.
        danger_threshold = preemption_time_cost * self.safety_margin_factor
        if current_slack <= danger_threshold:
            return ClusterType.ON_DEMAND

        # Rule 2: Opportunistic Spot Usage.
        # If Spot is available and we are not in the danger zone, always use it
        # as it is the most cost-effective way to make progress.
        if has_spot:
            return ClusterType.SPOT

        # Rule 3: Spot is Unavailable.
        # Decide between waiting for Spot (NONE) or making progress on the more
        # expensive On-Demand instance.
        # We define a "wait" threshold, which is a more comfortable level of
        # slack.
        wait_threshold = preemption_time_cost * self.wait_slack_threshold_factor
        
        if current_slack > wait_threshold:
            # If we have plenty of slack, we can afford to wait for Spot to
            # become available again, saving costs.
            return ClusterType.NONE
        else:
            # If our slack is below the comfort level (but not yet dangerous),
            # we should use On-Demand to make progress and build our slack back
            # up, preventing it from dropping into the danger zone.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        """
        Instantiates the class from command-line arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)