from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide which cluster type to use for the next step.
        Strategy:
        1. Calculate the 'point of no return': the latest time we must switch to On-Demand
           to guarantee finishing by the deadline, accounting for restart overhead.
        2. If we are approaching this point (slack is low), force On-Demand.
        3. If we have slack:
           - Use Spot if available (cheapest progress).
           - Use NONE if Spot is unavailable (wait for Spot to return to save money).
        """
        # Gather state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        total_work = self.task_duration
        gap = self.env.gap_seconds
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, total_work - work_done)
        
        # If work is done, stop
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        time_left = deadline - elapsed
        
        # Calculate time needed if we commit to On-Demand now.
        # We include 'overhead' in this calculation to be conservative.
        # This ensures that even if we are currently on Spot or None, we reserve
        # enough time to pay the penalty of switching to OD and still finish.
        # It also prevents switching away from OD unless we have enough buffer 
        # to pay the overhead of potentially coming back to OD later.
        time_needed_conservative = work_remaining + overhead
        
        # Define a safety margin. Since simulation happens in discrete steps (gaps),
        # we must ensure we don't cross the deadline threshold in the next step.
        # 2.0x gap provides a robust buffer against step size and rounding.
        safety_margin = 2.0 * gap
        
        slack = time_left - time_needed_conservative
        
        # Critical Path: If slack is exhausted, we must use On-Demand to meet deadline.
        if slack < safety_margin:
            return ClusterType.ON_DEMAND
            
        # Economy Path: We have time buffer. Minimize cost.
        if has_spot:
            # Spot is available and we have slack. Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable. Since we have slack, we wait (NONE) 
            # rather than burning money on OD.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
