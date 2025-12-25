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
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        total_duration = self.task_duration
        
        # Calculate progress and remaining work
        # self.task_done_time is a list of completed work segments
        progress = sum(self.task_done_time)
        remaining_work = total_duration - progress
        
        # If work is effectively completed
        if remaining_work <= 1e-6:
            return ClusterType.NONE
            
        time_remaining = deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Safety Calculation:
        # We must switch to On-Demand (OD) if we are approaching the point where
        # time_remaining == remaining_work + restart_overhead.
        # We add a buffer to account for the discrete nature of time steps (gap).
        # If we wait one more gap while unavailable, we lose 'gap' time.
        # We use 3.0 * gap to be conservative against discrete stepping and potential float variances.
        safety_buffer = 3.0 * gap
        must_run_od_threshold = remaining_work + overhead + safety_buffer
        
        if time_remaining < must_run_od_threshold:
            # We are entering the danger zone where any further delay risks missing the deadline.
            # We must use the guaranteed resource (OD) immediately.
            return ClusterType.ON_DEMAND
            
        # If we have slack:
        if has_spot:
            # Use Spot to minimize cost
            return ClusterType.SPOT
        else:
            # Spot unavailable, but we have slack.
            # Do not spend money on OD yet; wait for Spot to return or for slack to reduce.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)