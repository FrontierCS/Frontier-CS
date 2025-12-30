from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the cluster type for the next time step.
        Strategy:
        1. Calculate the latest possible moment we must start On-Demand to meet the deadline (Slack).
        2. If we are close to that threshold, force On-Demand to guarantee completion.
        3. If we have slack:
           - Use Spot if available (cheapest).
           - If Spot is unavailable, return NONE (wait) to save money, assuming Spot might return 
             or we can switch to On-Demand later before the deadline.
        """
        # Current state
        elapsed_time = self.env.elapsed_seconds
        step_gap = self.env.gap_seconds
        
        # Calculate progress
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - work_done)
        
        # If job is finished
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        time_until_deadline = self.deadline - elapsed_time
        
        # Calculate time required to finish if we commit to On-Demand now.
        # If we are not currently on On-Demand, we incur restart overhead.
        # If we are already on On-Demand, we don't incur new overhead (continuing).
        required_time_od = work_remaining
        if last_cluster_type != ClusterType.ON_DEMAND:
            required_time_od += self.restart_overhead
            
        # Safety Buffer Calculation:
        # If we choose NONE (wait) this step, we consume 'step_gap' time.
        # We must ensure that at (elapsed_time + step_gap), we still have enough time to finish.
        # i.e., (time_until_deadline - step_gap) >= required_time_od
        # We use a multiplier (2.0) and a small constant for float safety/robustness.
        safety_buffer = (2.0 * step_gap) + 30.0
        
        # Critical Condition: Check if we are approaching the point of no return
        if time_until_deadline <= required_time_od + safety_buffer:
            return ClusterType.ON_DEMAND
            
        # Flexible Zone: prioritize cost
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable, but we have slack. 
            # Wait (NONE) to avoid paying for On-Demand prematurely.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)