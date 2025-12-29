from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Retrieve current environment state
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Calculate progress
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # Job completed check (handle float precision)
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        # Calculate the panic threshold.
        # We must switch to On-Demand if the remaining time is barely enough to finish the work
        # plus the restart overhead (in case we need to start/restart).
        # We include a safety buffer of 2 time steps (gap) to handle simulation granularity.
        # Logic: If we wait (NONE) or fail on Spot this step, we lose 'gap' seconds.
        # We must ensure that at (current_time + gap), we still have enough time to finish on OD.
        # Threshold = Deadline - Work_Remaining - Restart_Overhead - Safety_Buffer
        
        safety_buffer = self.restart_overhead + (2.0 * gap)
        panic_threshold = self.deadline - work_remaining - safety_buffer
        
        # Priority 1: Guarantee Deadline (Hard Constraint)
        # If we are past the threshold, we strictly use On-Demand to avoid -100000 penalty.
        if current_time >= panic_threshold:
            return ClusterType.ON_DEMAND
            
        # Priority 2: Minimize Cost
        # If we have slack (current_time < panic_threshold), we prefer Spot or Waiting.
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is unavailable but we have slack, we choose NONE (wait).
        # Using OD here would waste money since we still have time to wait for cheap Spot.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)