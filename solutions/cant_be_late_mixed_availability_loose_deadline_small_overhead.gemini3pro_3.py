from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLate_Optimized"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve current state
        elapsed = self.env.elapsed_seconds
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        # If the task is effectively complete, stop incurring costs
        if remaining_work <= 1e-4:
            return ClusterType.NONE

        deadline = self.deadline
        time_left = deadline - elapsed
        
        # Parameters for decision making
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate the "Panic Threshold"
        # We must ensure that if we delay switching to reliable On-Demand resources,
        # we still have enough time to finish the job later.
        #
        # Required Time = Remaining Work + Restart Overhead
        # (Overhead is added because we might need to switch instance types or restart)
        #
        # We check if we will be safe at the START of the NEXT step.
        # If we choose SPOT or NONE now, we consume 'gap' seconds.
        # At next step, time_left will be (current_time_left - gap).
        # We need: (current_time_left - gap) >= (remaining_work + overhead)
        # So: current_time_left >= remaining_work + overhead + gap
        #
        # We use a safety multiplier (2.0 * gap) to account for jitter or boundary conditions.
        
        panic_threshold = remaining_work + overhead + (2.0 * gap)
        
        # Priority 1: Meet the Deadline
        if time_left < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # Priority 2: Minimize Cost (Use Spot if available)
        if has_spot:
            return ClusterType.SPOT
            
        # Priority 3: Save Money (Wait if Spot is unavailable and we have slack)
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
