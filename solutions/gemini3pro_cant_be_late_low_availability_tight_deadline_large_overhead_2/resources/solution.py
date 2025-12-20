from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "SafeThresholdStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Fetch environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        duration = self.task_duration
        overhead = self.restart_overhead
        
        # Calculate remaining work
        # self.task_done_time is a list of completed work segments in seconds
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, duration - work_done)
        
        # If work is finished, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE

        time_remaining = deadline - elapsed
        
        # Calculate Panic Threshold
        # This is the point of no return. If time_remaining drops below this,
        # we must use On-Demand to guarantee we meet the deadline.
        # Calculation:
        # 1. Work remaining: Time needed to execute the task
        # 2. Overhead: Time lost if we have to restart (worst case assumption)
        # 3. Buffer: Safety margin for simulation time steps (2x step size)
        buffer = 2.0 * gap
        panic_threshold = work_remaining + overhead + buffer
        
        # Decision Logic
        
        # 1. Survival Rule: If close to deadline, force On-Demand.
        # This ensures we don't risk waiting for Spot or getting preempted 
        # without enough time to recover.
        if time_remaining < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Economy Rule: If we have slack...
        if has_spot:
            # Use Spot instances if available (cheaper, makes progress)
            return ClusterType.SPOT
        else:
            # If Spot is unavailable, WAIT (NONE).
            # Since we are above the panic threshold, we have slack to burn.
            # Waiting is free, whereas running On-Demand is expensive.
            # We only switch to On-Demand when the panic threshold is crossed.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
