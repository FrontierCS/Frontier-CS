from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Current state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        total_duration = self.task_duration
        restart_overhead = self.restart_overhead
        
        # Calculate work remaining based on completed segments
        completed_work = sum(self.task_done_time)
        remaining_work = max(0.0, total_duration - completed_work)
        
        # Time remaining until the hard deadline
        time_left = deadline - elapsed
        
        # Safety buffer (seconds)
        # We use a 30-minute buffer to account for simulation step size and
        # ensuring we trigger the switch to On-Demand comfortably before the absolute limit.
        safety_buffer = 1800
        
        # Calculate time required if we switch to On-Demand immediately.
        # This includes the actual work time plus the restart overhead 
        # (assuming we might be starting fresh or switching types).
        time_needed_on_demand = remaining_work + restart_overhead
        
        # Calculate slack: extra time available beyond what is strictly needed for On-Demand completion.
        slack = time_left - time_needed_on_demand - safety_buffer
        
        # Strategy Logic:
        
        # 1. Panic Mode: If slack is negative, we are approaching the point of no return.
        #    We must switch to On-Demand immediately to guarantee finishing before the deadline.
        #    Cost optimization is secondary to meeting the deadline.
        if slack < 0:
            return ClusterType.ON_DEMAND
            
        # 2. Economy Mode: We have sufficient slack.
        #    If Spot instances are available, use them to minimize cost.
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Waiting Mode: Spot is unavailable, but we have time to spare.
        #    Wait (ClusterType.NONE) rather than paying for On-Demand.
        #    We consume slack time hoping for Spot availability.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)