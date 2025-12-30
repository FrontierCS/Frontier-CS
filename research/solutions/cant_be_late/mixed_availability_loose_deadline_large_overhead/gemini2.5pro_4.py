import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    A dynamic scheduling strategy that balances cost and the risk of missing the deadline.

    The core idea is to define a "critical time threshold". Before this time, the
    strategy prioritizes cost savings by using Spot instances whenever available. After
    this threshold, it switches to a risk-averse mode using On-Demand instances to
    guarantee timely completion.

    The critical time is calculated as the latest moment we can start the remaining work
    on a reliable On-Demand instance and still finish, even if we suffer one more
    Spot preemption right before starting.

    When Spot is unavailable and we are not yet in the critical zone, the strategy
    decides whether to wait (NONE) or use On-Demand based on the amount of available
    "slack" time. If the slack is substantial, it's worth waiting for the cheaper
    Spot instance to become available again. If the slack is running low, it's safer
    to make progress with On-Demand.
    """
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy with tunable hyperparameters.
        """
        # This factor determines how much slack we need to have (in multiples
        # of restart_overhead) before we are willing to wait for spot instances.
        # If slack is below this threshold, we use on-demand to not fall behind.
        self.wait_threshold_factor = 2.5

        # This factor adds an extra buffer to the critical time calculation.
        # A value > 1.0 makes the strategy more conservative, switching to
        # on-demand earlier. It essentially inflates the perceived cost of a
        # potential future preemption.
        self.safety_buffer_factor = 1.1

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a scheduling decision at each time step.
        """
        # Step 1: Calculate current progress and remaining work.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # Step 2: If the task is completed, do nothing to save cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        # Step 3: Determine the critical time threshold.
        # This is the "point of no return". If we reach this time, we must switch
        # to on-demand to guarantee finishing before the deadline, assuming one
        # more preemption could happen right now.
        time_needed_after_potential_failure = (
            work_remaining + self.restart_overhead * self.safety_buffer_factor
        )
        critical_start_time = self.deadline - time_needed_after_potential_failure

        current_time = self.env.elapsed_seconds

        # Step 4: Main decision logic based on whether we are in the critical zone.
        if current_time >= critical_start_time:
            # We are in the "critical zone" where we can't risk another preemption.
            # Use the reliable on-demand instance to finish the job.
            return ClusterType.ON_DEMAND
        else:
            # We have a time buffer (slack). We can afford to be cost-effective.
            if has_spot:
                # Spot is available and we have slack, so use the cheaper option.
                return ClusterType.SPOT
            else:
                # Spot is not available. Decide whether to wait or use on-demand.
                # The decision is based on how much slack we have.
                slack = critical_start_time - current_time

                # The waiting threshold is a heuristic. If our slack is greater
                # than this value, we can afford to wait for spot to become available.
                waiting_threshold = self.restart_overhead * self.wait_threshold_factor

                if slack > waiting_threshold:
                    # We have ample slack, so wait (do nothing) to save cost.
                    return ClusterType.NONE
                else:
                    # Our slack is running low. It's better to make progress
                    # with an on-demand instance than to risk waiting and
                    # falling into the critical zone.
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        """
        Instantiates the strategy from command-line arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)