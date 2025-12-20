import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    # --- Hyperparameters ---
    # This factor determines how aggressively we preserve our time cushion.
    # Higher value = more conservative (uses OD earlier), lower cost risk.
    # Lower value = more aggressive (waits for Spot longer), higher deadline risk.
    # A value of 5.0 means we want our time cushion to be at least 5x the
    # expected wait time for the next Spot instance.
    SAFETY_FACTOR = 5.0

    # Bayesian prior for estimating Spot availability. We assume a 20%
    # availability rate before observing any data, based on the problem's
    # [4%, 40%] range. This is a weak prior that is quickly updated by data.
    # Prior mean = P_SPOT_ALPHA_0 / (P_SPOT_ALPHA_0 + P_SPOT_BETA_0)
    P_SPOT_ALPHA_0 = 1.0
    P_SPOT_BETA_0 = 4.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy state. Called once before evaluation.
        """
        self.spot_avail_count = 0
        self.total_steps = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Core decision logic, called at each time step.
        """
        # 1. Update state for estimating spot availability
        self.total_steps += 1
        if has_spot:
            self.spot_avail_count += 1

        # 2. Calculate current progress and time metrics
        work_completed = sum(self.task_done_time)
        work_remaining = self.task_duration - work_completed

        # If the job is done, switch to NONE to minimize cost.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        # 3. PANIC MODE: Absolute deadline check
        # If the remaining work plus a buffer for one potential preemption is more
        # than the time left, we have no choice but to use On-Demand.
        # This is the critical backstop to guarantee finishing on time.
        if work_remaining + self.restart_overhead >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # 4. Main Decision Logic: Prefer Spot > Wait > On-Demand
        if has_spot:
            # Spot is available, cheap, and makes progress. It's the best option.
            return ClusterType.SPOT

        # If Spot is not available, the choice is between waiting (NONE) and
        # paying for progress (ON_DEMAND).

        # Estimate spot availability probability using our Bayesian tracker.
        alpha = self.P_SPOT_ALPHA_0 + self.spot_avail_count
        beta = self.P_SPOT_BETA_0 + (self.total_steps - self.spot_avail_count)
        p_spot_est = alpha / (alpha + beta)
        
        # Safeguard against division by zero if alpha_0 was 0 and no spot seen.
        if p_spot_est < 1e-9:
             p_spot_est = 1e-9

        # "Cushion" is our time slack: how long we can afford to do nothing
        # and still complete the job using On-Demand if necessary.
        cushion = time_to_deadline - work_remaining

        # We define a dynamic threshold for this cushion. If our cushion drops
        # below this threshold, the risk of waiting is too high, so we use OD.
        # The threshold is based on the expected wait time for a Spot instance.
        expected_wait_time = (1.0 / p_spot_est) * self.env.gap_seconds
        cushion_threshold = self.SAFETY_FACTOR * expected_wait_time
        
        # Enforce a minimum absolute cushion to be safe, especially in the beginning
        # when the spot probability estimate is not yet reliable. Two restart
        # overheads is a reasonable minimum buffer.
        min_cushion = 2.0 * self.restart_overhead
        
        final_threshold = max(cushion_threshold, min_cushion)
        
        if cushion < final_threshold:
            # Our slack is getting dangerously low. It's time to pay for the
            # guaranteed progress of an On-Demand instance.
            return ClusterType.ON_DEMAND
        else:
            # We have a healthy amount of slack. We can afford to wait for a
            # cheaper Spot instance to become available.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required classmethod for the evaluator to instantiate the solution.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
