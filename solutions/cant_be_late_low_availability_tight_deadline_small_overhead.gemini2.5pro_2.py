import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_rate_threshold_v1"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's state, including the EMA for spot
        availability and the parameters for the adaptive threshold.
        """
        # Initial guess for spot availability. The problem states a range of
        # 4-40%, so we start with a reasonable middle value.
        self.p_ema = 0.20

        # EMA decay factor. beta=0.995 corresponds to an effective memory
        # of approximately 1 / (1 - 0.995) = 200 steps. This provides a
        # stable yet responsive estimate of availability.
        self.beta = 0.995

        # Constants for a linear mapping from p_ema to the rate threshold.
        # R_thresh(p) = THRESH_A * p + THRESH_B
        # These parameters are derived by setting target buffer times for
        # worst-case (p=0.04) and best-case (p=0.4) availability scenarios,
        # ensuring a balance between aggressive cost-saving and conservative
        # deadline-meeting.
        # For p=0.04, we target a 2h safety buffer -> R_min = 0.96
        # For p=0.4, we target a 0.5h safety buffer -> R_max = 0.995
        p_min, p_max = 0.04, 0.40
        r_min, r_max = 0.96, 0.995
        self.THRESH_A = (r_max - r_min) / (p_max - p_min)
        self.THRESH_B = r_min - self.THRESH_A * p_min

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a decision at each time step based on an adaptive threshold policy.
        """
        # 1. Update our estimate of spot availability using EMA.
        current_availability = 1.0 if has_spot else 0.0
        self.p_ema = self.beta * self.p_ema + (1.0 - self.beta) * current_availability

        # 2. Calculate remaining work and time.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the job is finished, stop and incur no further cost.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # 3. Handle critical situations: if no slack is left, we must use
        # On-Demand to guarantee completion. This also handles cases where
        # the deadline has already passed.
        if time_to_deadline <= work_remaining:
            return ClusterType.ON_DEMAND

        # 4. Main decision logic.
        # Always use Spot when available and not in a critical state, as it is
        # the most cost-effective way to make progress.
        if has_spot:
            return ClusterType.SPOT

        # If Spot is unavailable, decide between waiting (NONE) or using On-Demand.
        # The decision is based on comparing a "required progress rate" to a
        # dynamic threshold that adapts to observed spot availability.
        required_rate = work_remaining / time_to_deadline

        # We clip p_ema to the known [0.04, 0.4] range for robustness,
        # preventing extreme threshold values from noisy estimates early on.
        p_clipped = max(0.04, min(0.4, self.p_ema))
        rate_threshold = self.THRESH_A * p_clipped + self.THRESH_B

        if required_rate > rate_threshold:
            # Urgency is high; the risk of waiting is too great. Use On-Demand.
            return ClusterType.ON_DEMAND
        else:
            # We have enough of a buffer given the availability outlook.
            # Wait for a Spot instance to become available.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Instantiates the strategy from command-line arguments.
        This strategy does not require any custom arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
