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
        # Calculate current progress
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If task is complete, stop
        if work_remaining <= 0:
            return ClusterType.NONE
            
        elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed
        gap = self.env.gap_seconds

        # Calculate the slack time (buffer).
        # We need to preserve enough time to finish the work on On-Demand instances
        # even in the worst case where we have to restart (paying the overhead).
        # worst_case_time_needed = work_remaining + restart_overhead
        # buffer = time_available - worst_case_time_needed
        # We subtract overhead regardless of current state to prevent flapping 
        # (switching OD->NONE->OD) near the threshold and to be conservative.
        buffer = time_remaining - (work_remaining + self.restart_overhead)
        
        # Define a safety threshold.
        # If we choose NONE or SPOT this step, and make no progress (wait or spot dies),
        # we lose 'gap' seconds of buffer. We must ensure buffer remains non-negative 
        # for the next step decision.
        # Using 2.0 * gap adds a small robustness margin against floating point jitter.
        safety_threshold = 2.0 * gap

        # Critical Zone Strategy:
        # If our buffer drops below the safety threshold, we cannot risk waiting 
        # or relying on unreliable Spot instances. Force On-Demand to guarantee deadline.
        if buffer < safety_threshold:
            return ClusterType.ON_DEMAND

        # Cost Optimization Strategy:
        # We have sufficient slack. We should prioritize cost.
        if has_spot:
            # Spot is available and is the cheapest option.
            return ClusterType.SPOT
        else:
            # Spot is unavailable. Since we have slack, we wait (NONE) for Spot to return
            # rather than paying the high cost of On-Demand immediately.
            # This consumes buffer but minimizes cost.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)
