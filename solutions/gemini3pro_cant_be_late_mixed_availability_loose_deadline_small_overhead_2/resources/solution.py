from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate progress and remaining work
        # task_done_time is a list of completed segment durations in seconds
        progress = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = self.task_duration - progress
        
        # If work is effectively done, stop
        if remaining_work <= 1e-3:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate Critical Threshold
        # We must switch to On-Demand if we are close to the point of no return.
        # The threshold accounts for:
        # 1. remaining_work: Actual computation needed
        # 2. restart_overhead: Time lost if we need to switch instance types
        # 3. gap_seconds: Worst-case delay before the next decision step
        # 4. padding: 600s (10 mins) safety margin for environment jitter/floating point errors
        
        # Note: All time units are in seconds
        safety_padding = 600.0
        threshold = (
            remaining_work + 
            self.restart_overhead + 
            self.env.gap_seconds + 
            safety_padding
        )
        
        # Panic Logic: If time remaining is critically low, force On-Demand
        if time_left <= threshold:
            return ClusterType.ON_DEMAND
            
        # Standard Logic: If we have slack, prefer Spot to save cost
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is unavailable but we have plenty of slack, wait (pause) 
        # to avoid paying On-Demand prices unnecessarily.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
