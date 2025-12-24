from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If work is completed, stop
        if work_remaining <= 0:
            return ClusterType.NONE

        # Get environment parameters
        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate Panic Threshold
        # We must switch to On-Demand if the time remaining approaches the minimum time 
        # required to finish with On-Demand (Work + Overhead).
        # We add a safety buffer (2 * gap) to ensure we can survive the current step 
        # if we choose to wait or if Spot fails, plus a margin for simulation granularity.
        # Threshold logic: Time needed to recover if we waste the current step.
        min_time_required = work_remaining + overhead + (gap * 2.0)
        
        # If time is critical, force On-Demand
        if time_left <= min_time_required:
            return ClusterType.ON_DEMAND
            
        # If we have slack time available
        if has_spot:
            # Prefer Spot instances to minimize cost
            return ClusterType.SPOT
        else:
            # If Spot is unavailable but we have slack, wait (NONE) 
            # to save money instead of running expensive On-Demand
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
