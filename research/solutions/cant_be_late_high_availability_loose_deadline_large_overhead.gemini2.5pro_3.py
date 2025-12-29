import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "AdaptiveCapacityStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the strategy's hyperparameters and state.
        This method is called once before the simulation starts.
        """
        # Hyperparameters
        self.ema_alpha = 0.05
        self.gamma = 1.15
        self.critical_slack_hours = 3.0
        
        # Initial state
        self.initial_p_avail_estimate = 0.70
        self.p_avail_estimate = self.initial_p_avail_estimate
        self.critical_slack_seconds = self.critical_slack_hours * 3600.0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decision-making function called at each time step.
        """
        # 1. Update internal state: Estimate spot availability using an EMA
        is_spot_available_now = 1.0 if has_spot else 0.0
        self.p_avail_estimate = (
            (1 - self.ema_alpha) * self.p_avail_estimate + 
            self.ema_alpha * is_spot_available_now
        )

        # 2. Calculate current progress and remaining work/time
        work_done_seconds = sum(end - start for start, end in self.task_done_time)
        work_remaining_seconds = self.task_duration - work_done_seconds

        if work_remaining_seconds <= 0:
            return ClusterType.NONE

        time_remaining_seconds = self.deadline - self.env.elapsed_seconds
        
        if time_remaining_seconds <= 0:
            return ClusterType.ON_DEMAND

        # 3. Emergency Mode: If slack is critically low, use On-Demand.
        # This is a safety net to prevent deadline misses at all costs.
        slack_seconds = time_remaining_seconds - work_remaining_seconds
        if slack_seconds <= self.critical_slack_seconds:
            return ClusterType.ON_DEMAND

        # 4. Core Logic: Compare projected spot capacity vs. required work.
        # This determines whether to be cost-saving (and wait for spot) or
        # progress-focused (and use on-demand as a fallback).

        # Use a floor for the availability estimate to handle the initial warm-up period
        # and prevent extreme decisions if availability drops to near zero.
        safe_p_avail_estimate = max(0.2, self.p_avail_estimate)

        # Estimate the total work we can accomplish using only spot instances.
        projected_spot_work_capacity = safe_p_avail_estimate * time_remaining_seconds
        
        # Multiply remaining work by a safety factor `gamma` to account for
        # estimation errors and un-modeled costs like preemption overheads.
        required_work_capacity_with_buffer = self.gamma * work_remaining_seconds

        if projected_spot_work_capacity > required_work_capacity_with_buffer:
            # "Comfortable" zone: Projected capacity is high. We can afford
            # to wait for spot to save costs.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            # "Prudent" zone: Time buffer is shrinking. We must make progress.
            # Use Spot if available, but fall back to On-Demand otherwise.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required boilerplate for the evaluator to instantiate the class.
        """
        args, _ = parser.parse_known_args()
        return cls(args)