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
        # This multiplier determines how much slack we need before we are willing
        # to wait for a spot instance (using NONE) rather than using a costly
        # on-demand instance. A higher value means we are more patient, saving
        # money at the risk of running out of time. Given the high cost of
        # on-demand (~3x spot), a relatively high patience level is beneficial.
        self.WAIT_BUFFER_MULTIPLIER = 15.0
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
        # Calculate the total work completed so far and the work remaining.
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the job is finished, we don't need any resources.
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate the time remaining until the hard deadline.
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # If the remaining work is more than the time left, we cannot possibly
        # finish. The best we can do is run on-demand to minimize how much we
        # miss the deadline by.
        if time_to_deadline < work_remaining:
            return ClusterType.ON_DEMAND

        # Slack is the critical metric: it's the extra time we have beyond the
        # bare minimum required to finish the job using on-demand instances.
        slack = time_to_deadline - work_remaining

        # The cost of a spot preemption is the time lost from the failed step
        # plus the restart overhead. This forms our "panic" threshold.
        cost_of_preemption = self.restart_overhead + self.env.gap_seconds

        # PANIC MODE: If our slack is less than the cost of a single preemption,
        # we cannot afford the risk of using a spot instance. We must use the
        # guaranteed on-demand instance to ensure progress.
        if slack < cost_of_preemption:
            return ClusterType.ON_DEMAND

        # If we reach here, we have enough slack to tolerate at least one preemption.

        if has_spot:
            # Spot is available and we have a sufficient safety margin.
            # This is the most cost-effective choice.
            return ClusterType.SPOT
        else:
            # Spot is not available. The choice is between waiting (NONE) and
            # making expensive progress (ON_DEMAND).

            # We define a "wait buffer," a larger slack threshold. If our slack
            # is above this, we can afford to wait for spot to become available.
            wait_buffer = self.WAIT_BUFFER_MULTIPLIER * cost_of_preemption

            if slack > wait_buffer:
                # We have ample slack. It's better to wait for a cheap spot
                # instance than to pay for an expensive on-demand one.
                return ClusterType.NONE
            else:
                # Our slack is no longer large enough to wait comfortably.
                # The risk of burning too much time is high, so we must make
                # progress using an on-demand instance.
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):  # REQUIRED: For evaluator instantiation
        """
        Instantiates the strategy from command-line arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
