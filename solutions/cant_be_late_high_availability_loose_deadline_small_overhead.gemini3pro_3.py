from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Calculate remaining work based on completed segments
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        # If task is effectively complete, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE
            
        # Current environment state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Time remaining until hard deadline
        time_left = deadline - elapsed
        
        # Safety Logic: Determine if we are close to the "Point of No Return".
        # We must verify that if we waste the current step (by choosing NONE or getting preempted on SPOT),
        # we still have enough time to finish the job using guaranteed ON_DEMAND instances.
        
        # Time available at the start of the next step
        time_available_next = time_left - gap
        
        # Time required to finish on ON_DEMAND from a cold start:
        # 1. Actual work remaining
        # 2. Restart overhead (assumed needed if we are switching to OD)
        # 3. Safety margin (2.0 * gap) to account for floating point jitter and step boundaries
        required_time = remaining_work + overhead + (2.0 * gap)
        
        # If we are nearing the threshold, force ON_DEMAND execution
        if time_available_next < required_time:
            return ClusterType.ON_DEMAND
            
        # Cost Optimization Logic:
        # If we have sufficient slack time:
        # 1. Prefer SPOT instances as they are significantly cheaper.
        # 2. If SPOT is unavailable, choose NONE (wait). 
        #    Waiting is free, whereas using ON_DEMAND is expensive.
        #    Since we have slack, it is statistically better to wait for SPOT to return.
        
        if has_spot:
            return ClusterType.SPOT
            
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
