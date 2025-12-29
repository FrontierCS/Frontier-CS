import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLate_Solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the strategy.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide the cluster type for the next time step.
        Strategies:
        1. Calculate Slack (Time Remaining - Work Remaining).
        2. Determine a safety threshold based on restart overhead.
        3. If Slack < Threshold, use ON_DEMAND to guarantee deadline.
        4. If Slack is sufficient:
           - Use SPOT if available (cheapest).
           - Use NONE if SPOT unavailable (wait to save money, consuming slack).
        """
        # Calculate work remaining
        # task_done_time is a list of completed segments in seconds
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        # If work is effectively done, stop
        if work_rem <= 1e-6:
            return ClusterType.NONE

        # Calculate time state
        elapsed = self.env.elapsed_seconds
        time_rem = self.deadline - elapsed
        
        # Calculate Slack: The amount of time we can afford to not make progress
        slack = time_rem - work_rem
        
        # Calculate Threshold:
        # We must switch to On-Demand before (Slack < Restart Overhead).
        # If we wait longer, the overhead of starting On-Demand will eat the remaining slack 
        # below zero, making it impossible to finish on time.
        # We add a padding of 3 time steps to account for discrete simulation steps.
        padding = 3.0 * self.env.gap_seconds
        threshold = self.restart_overhead + padding
        
        # Critical Condition: Not enough slack to gamble on Spot or Wait.
        if slack < threshold:
            return ClusterType.ON_DEMAND
        
        # Safe Condition: Optimize for cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable, but we have slack.
            # Pause (NONE) to save money and wait for Spot availability.
            # This consumes slack. If slack drops below threshold, we will switch to OD.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)