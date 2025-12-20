from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostOptimizedStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # Check if job is finished
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        # Calculate slack
        # We assume conservatively that we might need to incur restart overhead
        time_needed = work_remaining + self.restart_overhead
        slack = time_remaining - time_needed
        
        # Define safety buffer
        # If slack falls below this threshold, we must use On-Demand to guarantee completion.
        # We use 5x restart overhead (approx 15 mins) to handle potential interruptions and step gaps.
        safety_buffer = 5 * self.restart_overhead
        if hasattr(self.env, 'gap_seconds') and self.env.gap_seconds:
            safety_buffer = max(safety_buffer, 4 * self.env.gap_seconds)
            
        # Critical state: Not enough slack to risk Spot interruptions or waiting
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND
            
        # Safe state: Prefer Spot instances to minimize cost
        if has_spot:
            return ClusterType.SPOT
            
        # Safe state but no Spot: Wait (NONE) to save money since we have slack
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
