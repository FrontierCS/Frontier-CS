from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate amount of work already completed
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If work is essentially complete, do nothing
        if remaining_work <= 1e-6:
            return ClusterType.NONE
            
        # Calculate time remaining until the hard deadline
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate the time required to finish if we switch to (or stay on) On-Demand NOW.
        # If we are not currently running On-Demand, we incur a restart overhead.
        # Note: If we are currently running OD (even if still in overhead phase), 
        # we don't add a *new* overhead penalty to the estimate.
        overhead_penalty = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_penalty = self.restart_overhead
            
        time_needed_on_od = remaining_work + overhead_penalty
        
        # Safety Buffer Calculation:
        # 1. We need to account for the simulation step size (gap_seconds). If we don't act now,
        #    our next chance is in `gap_seconds`.
        # 2. Add a conservative padding (e.g., 600 seconds/10 mins) to handle floating point 
        #    variations or edge cases, ensuring we don't miss the deadline.
        #    Better to pay slightly more for OD than to incur the -100,000 penalty.
        buffer = self.env.gap_seconds + 600.0
        
        # Critical Threshold Check
        # If the time remaining is less than what we need to finish on OD (plus buffer),
        # we must strictly prioritize the deadline over cost.
        if time_left < (time_needed_on_od + buffer):
            return ClusterType.ON_DEMAND
            
        # Cost Optimization Strategy
        # If we are not in the critical "danger zone", we aim to minimize cost.
        if has_spot:
            # Spot is available and cheap (approx 1/3 cost of OD).
            return ClusterType.SPOT
        else:
            # Spot is unavailable. Since we have sufficient slack (time_left > needed + buffer),
            # we can afford to pause (NONE) and wait for Spot to return, 
            # rather than paying for expensive On-Demand immediately.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)