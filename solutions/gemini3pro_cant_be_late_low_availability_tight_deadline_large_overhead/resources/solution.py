from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "AdaptiveSafeScheduler"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment status
        elapsed_time = self.env.elapsed_seconds
        deadline = self.deadline
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - work_done)
        
        # Calculate time left until deadline
        time_left = deadline - elapsed_time
        
        # Define safety threshold
        # We must switch to On-Demand if the time remaining allows just enough time 
        # to finish the work plus the restart overhead, with a safety buffer.
        # Buffer accounts for discrete time steps and ensures we don't cut it too close.
        # Using overhead as part of buffer provides robustness against one failed switch cycle.
        safety_buffer = overhead + (2.0 * gap)
        
        # Worst-case time required to finish if we switch to OD right now
        required_time = remaining_work + overhead + safety_buffer
        
        # 1. Safety Check: If we are nearing the point of no return, force On-Demand.
        if time_left < required_time:
            return ClusterType.ON_DEMAND
            
        # 2. Cost Optimization: If we have slack, try to use Spot.
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Wait: If Spot is unavailable and we are safe, wait (save money).
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
