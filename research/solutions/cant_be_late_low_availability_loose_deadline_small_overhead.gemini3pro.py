import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostOptimizedSolution"

    def __init__(self, args=None):
        super().__init__()
        # Safety buffer of 1 hour (3600 seconds) to ensure we don't miss the deadline
        # due to step granularity or minor overhead miscalculations.
        self.safety_buffer = 3600.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        # task_done_time is a list of completed work segments in seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        
        # Priority 1: Always prefer Spot instances when available
        if has_spot:
            # Optimization: If we are already running On-Demand and the remaining work 
            # is extremely short, switching to Spot might be more expensive due to restart overhead.
            # Assuming Price_OD (~3) vs Price_Spot (~1), break-even is roughly when
            # remaining work < overhead / 2.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if work_remaining < (self.restart_overhead * 0.5):
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Priority 2: Use On-Demand if we are running out of time (Slack check)
        # Calculate how much time we need to finish if we start On-Demand now.
        
        # If we are not currently running On-Demand, we will incur a restart overhead penalty.
        overhead_penalty = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_penalty = self.restart_overhead
            
        time_needed_on_od = work_remaining + overhead_penalty
        slack = time_remaining - time_needed_on_od
        
        # We need a buffer to ensure we react in time (at least one step size).
        # We also add the safety_buffer to handle any unforeseen delays or granularities.
        current_threshold = self.safety_buffer + self.env.gap_seconds
        
        if slack < current_threshold:
            return ClusterType.ON_DEMAND
            
        # Priority 3: Wait to save money (consume slack)
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)