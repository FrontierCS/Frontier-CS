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
        Decides which cluster type to use at the current time step.
        Prioritizes meeting the hard deadline, then minimizes cost by using Spot instances.
        """
        # Calculate progress
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If task is complete, stop using resources
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        # Time calculations
        elapsed_time = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed_time
        
        # Calculate strict time required to finish using On-Demand
        # If we are not currently On-Demand, we must assume we pay the restart overhead to switch
        switch_overhead = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_overhead = self.restart_overhead
            
        time_needed_od = work_remaining + switch_overhead
        
        # Slack is the excess time we have before we MUST be on On-Demand to finish
        slack = time_remaining - time_needed_od
        
        # Safety buffer calculation
        # We add a conservative buffer to handle:
        # 1. Discrete time step quantization (gap_seconds)
        # 2. Potential delays or variations
        # 10 minutes (600s) + 2 steps is chosen to be safe against the -100,000 penalty
        safety_buffer = 600.0 + (2.0 * self.env.gap_seconds)
        
        # Decision Logic:
        
        # 1. Critical Phase: If slack drops below safety margin, forced to use On-Demand
        # This guarantees we meet the deadline (primary constraint)
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND
            
        # 2. Opportunistic Phase: If we have slack, try to use cheap Spot instances
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Waiting Phase: If Spot is unavailable but we have slack, wait (NONE)
        # This saves money compared to running On-Demand unnecessarily early
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)