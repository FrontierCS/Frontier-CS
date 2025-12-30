import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Must return self.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Calculate amount of work completed
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        
        # Calculate remaining work
        work_remaining = self.task_duration - work_done
        
        # If work is effectively done, stop
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        # Current simulation state
        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time
        
        # Environment parameters
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Pricing constants (approximate from problem description)
        PRICE_OD = 3.06
        PRICE_SPOT = 0.97

        # Calculate strict time required to finish using On-Demand (safe path).
        # If we are currently running OD, we don't incur restart overhead.
        # If we are NOT running OD (NONE or SPOT), we incur overhead to start/switch.
        if last_cluster_type == ClusterType.ON_DEMAND:
            time_needed_od = work_remaining
        else:
            time_needed_od = work_remaining + overhead
            
        # Slack: How much extra time we have before we MUST commit to OD.
        slack = time_to_deadline - time_needed_od
        
        # Panic Threshold:
        # If we wait (return NONE), we lose 'gap' seconds of slack.
        # We must ensure Slack > gap to safely wait.
        # Using 1.5 * gap as a safety buffer against floating point jitter.
        panic_threshold = 1.5 * gap

        if has_spot:
            # Spot is available. 
            # Strategy: Use Spot unless switching from OD is inefficient or unsafe.
            
            if last_cluster_type == ClusterType.ON_DEMAND:
                # We are currently on OD. Switching to Spot incurs overhead.
                
                # 1. Safety Check: Can we afford the overhead time penalty?
                time_needed_spot = work_remaining + overhead
                slack_if_switch = time_to_deadline - time_needed_spot
                
                if slack_if_switch < panic_threshold:
                    # Too risky to switch (might miss deadline due to overhead). Stay OD.
                    return ClusterType.ON_DEMAND
                
                # 2. Cost Check: Is switching actually cheaper?
                # Cost to stay OD: Price_OD * Time_Left
                # Cost to switch: Price_Spot * (Time_Left + Overhead)
                cost_stay = PRICE_OD * work_remaining
                cost_switch = PRICE_SPOT * (work_remaining + overhead)
                
                if cost_switch < cost_stay:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # Not on OD (either NONE or SPOT).
                # Since Spot is available and cheaper, use it.
                return ClusterType.SPOT

        else:
            # Spot is unavailable.
            # Strategy: Wait (NONE) to save money, unless Slack is critical.
            
            if slack < panic_threshold:
                # Critical: Must use On-Demand to guarantee deadline.
                return ClusterType.ON_DEMAND
            else:
                # Safe: Wait for Spot to return.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)