from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work (total duration - work done so far)
        done_work = sum(self.task_done_time)
        work_rem = self.task_duration - done_work
        
        # If work is completed, stop
        if work_rem <= 0:
            return ClusterType.NONE
            
        # Calculate remaining time until deadline
        time_rem = self.deadline - self.env.elapsed_seconds
        
        # Safety buffer calculation
        # We need to ensure we can finish on On-Demand even in the worst case.
        # Worst case includes paying the restart overhead to switch/start On-Demand.
        # We add a padding of 3 time steps to handle discrete simulation steps safely.
        gap = self.env.gap_seconds
        padding = 3.0 * gap
        
        # The threshold is the point of no return:
        # If we wait longer than this, we might not finish even with On-Demand.
        panic_threshold = work_rem + self.restart_overhead + padding
        
        # Critical Zone: Must use On-Demand to guarantee deadline
        if time_rem <= panic_threshold:
            return ClusterType.ON_DEMAND
            
        # Safe Zone: Prefer Spot to save cost
        if has_spot:
            return ClusterType.SPOT
            
        # Safe Zone but no Spot: Pause (NONE) to save money/slack
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)