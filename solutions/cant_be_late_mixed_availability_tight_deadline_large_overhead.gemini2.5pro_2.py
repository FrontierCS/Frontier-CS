from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "rate_based_adaptive_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the strategy's parameters. This method is called once before
        the simulation starts.
        """
        # EMA (Exponential Moving Average) alpha for smoothing the spot
        # availability estimate. A small alpha means the estimate adapts slowly
        # and has a long "memory".
        self.ema_alpha = 0.005

        # A safety margin for the decision threshold. We will only use Spot if its
        # estimated availability is comfortably higher than the required progress rate.
        # A value closer to 1.0 is more aggressive (cost-saving), while a smaller
        # value is more conservative (safer).
        self.safety_factor = 0.98

        # Initial guess for spot availability. We start optimistically to leverage
        # cheap spot instances from the beginning in high-availability environments.
        # The EMA will quickly correct this guess if the environment is different.
        self.initial_p_spot_hat = 0.95

        # State variable for the spot availability estimate.
        self.p_spot_hat = self.initial_p_spot_hat
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        This method is called at each timestep to decide which cluster type to use.
        """
        # 1. Update the online estimate of spot availability using EMA.
        current_observation = 1.0 if has_spot else 0.0
        self.p_spot_hat = self.ema_alpha * current_observation + (1.0 - self.ema_alpha) * self.p_spot_hat

        # 2. Calculate the current state of the job.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the job is already finished, do nothing to save costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time

        # 3. Failsafe: If the remaining work is more than or equal to the time left,
        # we have no slack. We must use the guaranteed ON_DEMAND instance.
        if work_remaining >= time_remaining:
            return ClusterType.ON_DEMAND

        # 4. Core Logic: Compare required progress rate with estimated spot performance.
        required_rate = work_remaining / time_remaining

        # The decision threshold is based on our adaptive estimate of spot availability,
        # discounted by a safety factor.
        decision_threshold = self.p_spot_hat * self.safety_factor

        if required_rate > decision_threshold:
            # Urgency is high. The required rate to meet the deadline is higher than
            # what we can reliably expect from spot instances. Use ON_DEMAND to catch up.
            return ClusterType.ON_DEMAND
        else:
            # We are on track or ahead of schedule. We can use cheaper options.
            if has_spot:
                # Spot is available and we have enough buffer. Use SPOT for max cost savings.
                return ClusterType.SPOT
            else:
                # Spot is not available. Decide between pausing (NONE) or working (ON_DEMAND).
                # We perform a one-step lookahead to see if pausing is too risky.
                gap = self.env.gap_seconds
                time_if_we_wait = time_remaining - gap

                # If waiting one step makes it impossible to finish, we must work.
                if time_if_we_wait <= work_remaining:
                    return ClusterType.ON_DEMAND

                # Calculate what the required rate would be after waiting for one step.
                rate_if_we_wait = work_remaining / time_if_we_wait

                if rate_if_we_wait > decision_threshold:
                    # Waiting for even one step would push us into the "urgent" zone.
                    # It's safer to use ON_DEMAND now to maintain our buffer.
                    return ClusterType.ON_DEMAND
                else:
                    # We have enough of a time buffer to safely wait for a spot instance
                    # to potentially become available in the next step. Use NONE to save cost.
                    return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        A required class method for the evaluation framework.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
