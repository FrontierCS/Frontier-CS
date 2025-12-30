from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        # self.task_done_time is a list of completed segments
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If work is effectively done, stop to save cost
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        # Current time and deadline
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_remaining = deadline - elapsed
        
        # Constants
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Safety Threshold Calculation (Panic Line)
        # We must ensure we have enough time to finish using On-Demand (OD) in the worst case.
        # Time required on OD = Remaining Work + Restart Overhead (to launch/switch to OD)
        # We add a safety buffer (2 * gap) to account for discrete time stepping and precision.
        # This condition acts as a "Point of No Return". Once crossed, we switch to OD and stay there.
        # We include overhead in the check to ensure that if we are NOT on OD, we leave enough room to switch.
        # If we ARE on OD, this threshold ensures we don't switch back to Spot unless we have gained 
        # significant slack (unlikely) and can afford the overhead to return to OD later.
        
        panic_threshold = work_remaining + overhead + (2.0 * gap)
        
        if time_remaining <= panic_threshold:
            return ClusterType.ON_DEMAND
        
        # If we have sufficient time buffer, prioritize cost savings
        if has_spot:
            return ClusterType.SPOT
        else:
            # If Spot is unavailable and we have slack, pause (NONE) to wait for Spot
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)