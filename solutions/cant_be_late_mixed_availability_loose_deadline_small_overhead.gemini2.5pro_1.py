import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy parameters.
        """
        # Smoothing factor for the Exponential Moving Average (EMA) of spot availability.
        self.ema_alpha = 0.0025

        # Safety factor to create a time buffer over the theoretical minimum.
        self.risk_aversion_factor = 1.15

        # Slowness factor threshold for "panic mode".
        self.panic_threshold = 1.05

        # State variable for the availability estimate, lazily initialized.
        self.estimated_p = None
        
        return self

    def _get_work_remaining(self) -> float:
        """Calculates the total amount of compute time remaining."""
        total_done_time = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - total_done_time
        return max(0.0, work_remaining)

    def _update_availability_estimate(self, has_spot: bool):
        """Updates the EMA of spot availability."""
        current_availability = 1.0 if has_spot else 0.0
        self.estimated_p = (self.ema_alpha * current_availability +
                            (1 - self.ema_alpha) * self.estimated_p)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Core decision logic for each time step.
        """
        # Initialize availability estimate on the first step, then update with EMA.
        if self.estimated_p is None:
            self.estimated_p = 1.0 if has_spot else 0.0
        else:
            self._update_availability_estimate(has_spot)

        work_remaining = self._get_work_remaining()

        # If the job is finished, do nothing to save cost.
        if work_remaining < 1e-6:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # Safeguard: if deadline has passed, use On-Demand.
        if time_to_deadline <= 0:
            return ClusterType.ON_DEMAND

        # The "slowness factor" is the core metric: ratio of remaining time to remaining work.
        slowness_factor = time_to_deadline / work_remaining

        # Decision Rule 1: Panic Mode
        # If slack is critically low, use On-Demand to guarantee completion.
        if slowness_factor < self.panic_threshold:
            return ClusterType.ON_DEMAND

        # Decision Rule 2: Greedy Spot Usage
        # If not in panic mode and spot is available, always use it.
        if has_spot:
            return ClusterType.SPOT

        # Decision Rule 3: Wait or Use On-Demand
        # If spot is not available, decide between waiting or using On-Demand.
        else:
            # Use a floor for the availability estimate to prevent division by zero.
            p_effective = max(self.estimated_p, 0.01)

            # Required slowness = 1 / p_effective, plus a risk aversion buffer.
            required_slowness_for_spot = (1.0 / p_effective) * self.risk_aversion_factor

            if slowness_factor < required_slowness_for_spot:
                # Time buffer is insufficient to risk waiting. Use On-Demand.
                return ClusterType.ON_DEMAND
            else:
                # We have enough buffer to wait for spot to become available.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Instantiates the strategy from command-line arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
