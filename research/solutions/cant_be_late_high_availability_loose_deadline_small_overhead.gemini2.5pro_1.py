import argparse
import math

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    """
    An adaptive scheduling strategy that balances cost and completion time.

    The core idea is to continuously estimate the availability of Spot instances
    and use this estimate to decide whether it's safe to rely on them.

    1.  **Online Availability Estimation**: The strategy maintains a running estimate
        of Spot availability (`p_spot_est`). It starts with an optimistic prior
        belief (e.g., 75% availability) and updates this belief at every time
        step based on real-world observations. This is a Bayesian approach that
        allows the strategy to adapt to the specific conditions of each trace.

    2.  **Required Rate Calculation**: At any point, the strategy calculates the
        `required_rate = work_remaining / time_to_deadline`. This represents the
        average speed needed from a 100% reliable resource (like On-Demand) to
        finish exactly at the deadline.

    3.  **Decision Threshold**: The decision to switch from Spot to On-Demand is
        governed by a simple inequality:
        `required_rate * URGENCY_FACTOR > p_spot_est`

        - If true, it means the required pace is too high to be reliably met by
          Spot instances. The strategy switches to On-Demand to guarantee progress.
        - If false, it means there is sufficient slack to rely on the cheaper Spot
          option. If Spot is available, it's used. If not, the strategy waits
          (`NONE`), consuming slack instead of money.

    The `URGENCY_FACTOR` (> 1.0) provides a safety buffer, ensuring the switch
    to On-Demand happens before the situation becomes truly unrecoverable. This
    proactive, adaptive approach aims to minimize cost by using Spot as much
    as possible without risking the deadline.
    """
    NAME = "adaptive_rate_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters and state.
        """
        # --- Hyperparameters ---
        # Prior belief about spot availability. Starts optimistically as the
        # problem states high availability regions (43-78%).
        self.PRIOR_P_SPOT = 0.75

        # Strength of our prior belief, measured in number of equivalent samples.
        # A moderate value allows for reasonably fast adaptation to the actual trace.
        self.PRIOR_SAMPLES = 20

        # Safety margin. We switch to On-Demand when the required progress rate
        # exceeds our estimated spot capacity by this factor.
        self.URGENCY_FACTOR = 1.10

        # --- State for estimating spot availability ---
        self.prior_available = self.PRIOR_SAMPLES * self.PRIOR_P_SPOT
        self.prior_unavailable = self.PRIOR_SAMPLES * (1 - self.PRIOR_P_SPOT)
        self.spot_seen_count = 0
        self.spot_available_count = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a scheduling decision at each time step.
        """
        # --- 1. Get current state ---
        work_remaining = self._get_remaining_work()

        # If the job is finished, do nothing to save costs.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # --- 2. Handle absolute deadlines (Points of No Return) ---
        # If we are past the deadline or have no time left, we have failed.
        # Use On-Demand as a last resort.
        if time_to_deadline <= 1e-9:
            return ClusterType.ON_DEMAND

        # If the remaining work is more than the time left, we MUST use the
        # fastest resource (On-Demand) continuously. There is no slack left.
        if work_remaining >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # --- 3. Update our estimate of Spot availability ---
        self.spot_seen_count += 1
        if has_spot:
            self.spot_available_count += 1

        # Bayesian estimate of p_spot = (alpha + successes) / (alpha + beta + trials)
        numer = self.prior_available + self.spot_available_count
        denom = self.prior_available + self.prior_unavailable + self.spot_seen_count
        p_spot_est = numer / denom

        # --- 4. Core Decision Logic ---
        # Calculate the required progress rate from now until the deadline,
        # assuming a 100% available resource.
        required_rate = work_remaining / time_to_deadline

        # The situation is critical if the required rate, scaled by our safety
        # factor, is greater than what we estimate Spot instances can provide.
        is_critical = (required_rate * self.URGENCY_FACTOR) > p_spot_est

        if is_critical:
            # The timeline is too tight to rely on Spot. Use the guaranteed resource.
            return ClusterType.ON_DEMAND
        else:
            # We have enough of a buffer to use cheaper options.
            if has_spot:
                # Spot is available and we're not in a critical phase, so use it.
                return ClusterType.SPOT
            else:
                # Spot is unavailable, but we're not critical. Wait for Spot to
                # become available again, consuming slack instead of money.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)