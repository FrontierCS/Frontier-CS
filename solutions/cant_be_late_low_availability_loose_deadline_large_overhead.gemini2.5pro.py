import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        We initialize parameters for a Bayesian estimation of spot availability.
        """
        # A Beta distribution is used to model our belief about spot probability.
        # The prior Beta(2.0, 8.0) corresponds to a mean probability of 0.2,
        # which is a reasonable starting point for the specified 4-40% availability range.
        self.alpha = 2.0
        self.beta = 8.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # 1. UPDATE STATE
        # Update our belief about spot availability based on the new observation.
        if has_spot:
            self.alpha += 1.0
        else:
            self.beta += 1.0

        # Calculate current progress and remaining work/time.
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done

        # If the job is finished, do nothing to minimize cost.
        if work_left <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        # The safety_buffer is the time slack we have if we complete the remaining
        # work using guaranteed on-demand instances.
        safety_buffer = time_left - work_left

        # 2. DECISION LOGIC
        # The strategy is risk-averse due to the high penalty for missing the deadline.

        # Rule A: CRITICAL PATH
        # If the safety buffer is zero or negative, we are behind schedule.
        # We must use ON_DEMAND to make guaranteed progress.
        if safety_buffer <= 0.0:
            return ClusterType.ON_DEMAND

        # Rule B: IDEAL CASE
        # If spot instances are available and it's safe to use them, do so.
        # "Safe" means that even if the instance is immediately preempted (costing
        # `restart_overhead` in time), we can still finish by the deadline.
        if has_spot and (safety_buffer >= self.restart_overhead):
            return ClusterType.SPOT

        # Rule C: DELIBERATION
        # We are in an intermediate state: either spot is unavailable, or it's too
        # risky to use. We must choose between waiting (NONE) or using ON_DEMAND.
        
        # We make this choice by estimating the time-cost of waiting for a spot
        # instance to appear.
        estimated_spot_prob = self.alpha / (self.alpha + self.beta)
        
        # Expected number of steps to wait for the next spot instance.
        # A small epsilon prevents division by zero if probability is near zero.
        expected_wait_steps = 1.0 / (estimated_spot_prob + 1e-9)
        
        # The expected buffer that will be consumed by waiting.
        expected_buffer_cost_to_wait = expected_wait_steps * self.env.gap_seconds

        # We should only wait if our current buffer is large enough to absorb
        # the expected waiting cost AND still leave us in a "safe" position
        # (i.e., with at least `restart_overhead` buffer) to use spot later.
        min_buffer_to_wait = expected_buffer_cost_to_wait + self.restart_overhead

        if not has_spot and safety_buffer > min_buffer_to_wait:
            # We have enough slack to wait for a cheap spot instance.
            return ClusterType.NONE
        else:
            # It's either too risky to use an available spot instance, or we don't
            # have enough buffer to wait for the next one. The prudent choice is
            # to use ON_DEMAND to make guaranteed progress.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
