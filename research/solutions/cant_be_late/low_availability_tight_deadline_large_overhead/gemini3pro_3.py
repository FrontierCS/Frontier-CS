from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLate"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the cluster type for the next time step.
        """
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Retrieve static constraints
        deadline = self.deadline
        duration = self.task_duration
        overhead = self.restart_overhead
        
        # Calculate progress
        work_done = sum(self.task_done_time)
        work_remaining = duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        # Safety Logic:
        # We must ensure that if we defer switching to On-Demand until the NEXT step,
        # we will still have enough time to finish.
        #
        # Time available at next step: deadline - (elapsed + gap)
        # Time required to finish on On-Demand (worst case with overhead): work_remaining + overhead
        
        time_at_next_step = elapsed + gap
        time_available_next = deadline - time_at_next_step
        time_required_od = work_remaining + overhead
        
        # Add a small buffer for floating point stability
        safety_buffer = 5.0
        
        # If the remaining time is approaching the bare minimum needed for On-Demand,
        # we must switch to On-Demand immediately to guarantee completion.
        if time_available_next < (time_required_od + safety_buffer):
            return ClusterType.ON_DEMAND
            
        # If we have slack, prioritize cost optimization
        if has_spot:
            return ClusterType.SPOT
            
        # If no spot is available and we are safe, wait to save money
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)