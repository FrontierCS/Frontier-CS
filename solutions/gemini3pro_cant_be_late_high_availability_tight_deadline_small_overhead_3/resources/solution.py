from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work based on completed segments
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        if remaining_work <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_until_deadline = self.deadline - current_time
        
        # Define safety buffer based on simulation step size
        # Use a default if gap_seconds is not yet established (though typically it is)
        gap = self.env.gap_seconds if self.env.gap_seconds else 60.0
        
        # Safety buffer: 2 steps + small epsilon to handle floating point/discretization
        safety_buffer = 2.0 * gap + 1.0
        
        # Calculate the "Panic Threshold"
        # If we switch to OD or restart, we incur overhead. 
        # We must switch to OD if time left is approaching (work + overhead).
        # We include overhead in the check even if currently on OD to prevent unsafe switching to Spot.
        min_required_time = remaining_work + self.restart_overhead + safety_buffer
        
        # 1. Critical Path: If close to deadline, force On-Demand
        if time_until_deadline <= min_required_time:
            return ClusterType.ON_DEMAND
            
        # 2. Economical Path: If we have slack, prefer Spot
        if has_spot:
            return ClusterType.SPOT
        
        # 3. Waiting Game: If Spot is unavailable but we have slack, wait (NONE) to save money
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
