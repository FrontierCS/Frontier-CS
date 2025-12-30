from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Retrieve current environment state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        duration = self.task_duration
        done = sum(self.task_done_time)
        restart_overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate work remaining
        work_remaining = max(0.0, duration - done)
        
        # If work is effectively done, stop using resources
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_remaining = deadline - elapsed
        
        # Define a safety buffer to prevent missing deadline due to discrete time steps or overheads.
        # 600 seconds (10 minutes) is a safe margin relative to the -100k penalty.
        # We also ensure it covers at least 2 simulation time steps.
        buffer = max(600.0, 2.0 * gap)
        
        # Determine effective overhead if we need to switch to On-Demand now.
        # If we are already on On-Demand, overhead is 0 (continuation).
        # If we are on Spot or None, we incur restart overhead to switch.
        switch_overhead = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_overhead = restart_overhead
            
        # Calculate the panic threshold:
        # If time_remaining drops below this, we MUST use On-Demand to guarantee completion.
        required_time = work_remaining + switch_overhead + buffer
        
        # Panic Mode: Hard deadline constraint
        if time_remaining <= required_time:
            return ClusterType.ON_DEMAND
            
        # Cost Minimization Mode: Use Spot if available
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot unavailable and we have slack, wait (NONE) to save money
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)