import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_rate_controller"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy parameters. This method is called once before the
        simulation starts.
        """
        # We use a Bayesian approach to estimate spot availability probability (p).
        # The prior is a Beta distribution, Beta(alpha, beta).
        # We start with a prior belief that p is around 0.2 (mean = 3 / (3+12)).
        # self.posterior_alpha tracks observed 'spot available' counts.
        # self.posterior_beta tracks observed 'spot unavailable' counts.
        self.posterior_alpha = 3.0
        self.posterior_beta = 12.0

        # This factor tunes the strategy's risk aversion.
        # A value < 1.0 makes the strategy more pessimistic about spot,
        # leading it to use On-Demand more readily to ensure it meets the deadline.
        # A value > 1.0 is more optimistic, waiting longer for spot instances,
        # which saves cost but increases the risk of missing the deadline.
        # Given the severe penalty for failure, a risk-averse setting is safer.
        self.urgency_factor = 0.95

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        This method is called at each timestep to decide which cluster type to use.
        """
        # 1. Update our estimate of spot availability based on the current observation.
        if has_spot:
            self.posterior_alpha += 1
        else:
            self.posterior_beta += 1
        
        p_estimate = self.posterior_alpha / (self.posterior_alpha + self.posterior_beta)

        # 2. Calculate the current state of the job.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE  # Job is finished.

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        if time_to_deadline <= 0:
            # We are at or past the deadline. We must use the guaranteed resource.
            return ClusterType.ON_DEMAND

        # 3. Apply the decision logic hierarchy.

        # PRIORITY 1: SAFETY NET
        # Check if we have entered the "point of no return", where we must use
        # On-Demand to guarantee completion. This is when the time left is less
        # than the work remaining plus a buffer for a potential restart.
        critical_time_needed = work_remaining + self.restart_overhead
        if time_to_deadline <= critical_time_needed:
            return ClusterType.ON_DEMAND
            
        # PRIORITY 2: GREEDY CHOICE
        # If spot instances are available, always use them. It's the most
        # cost-effective way to make progress.
        if has_spot:
            return ClusterType.SPOT
            
        # PRIORITY 3: CORE TRADE-OFF
        # If spot is not available, we must decide between paying for On-Demand
        # or waiting (and incurring no cost).
        
        # We calculate the required progress rate to finish exactly at the deadline.
        required_rate = work_remaining / time_to_deadline
        
        # We compare this required rate to our estimate of what spot can provide.
        # The urgency_factor makes us act more conservatively.
        urgency_threshold = self.urgency_factor * p_estimate
        
        if required_rate > urgency_threshold:
            # The required rate is higher than what we can expect from spot.
            # The situation is becoming urgent, so we use On-Demand to make
            # guaranteed progress and reduce the future required rate.
            return ClusterType.ON_DEMAND
        else:
            # The required rate is low enough that we can afford to wait.
            # We bet that spot instances will become available soon enough.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required classmethod for the evaluation environment to instantiate the
        strategy.
        """
        args, _ = parser.parse_known_args()
        return cls(args)