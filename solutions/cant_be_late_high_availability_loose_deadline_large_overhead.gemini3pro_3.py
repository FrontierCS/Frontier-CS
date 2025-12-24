from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostOptimizedDeadlineStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If the task is already completed (or effectively so), stop.
        if work_remaining <= 0:
            return ClusterType.NONE
            
        # Calculate time remaining until the hard deadline
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Get environment parameters
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate Safety Threshold
        # We must switch to On-Demand (OD) if we are close to running out of time.
        # The absolute minimum time to finish on OD is: work_remaining + overhead (boot time).
        # We add a safety buffer consisting of:
        # 1. Another 'overhead' duration: To account for the worst case where we try Spot, 
        #    pay the boot penalty, fail immediately, and then have to switch to OD (paying overhead again).
        # 2. Multiple 'gap' durations: To handle the discrete nature of the simulation steps.
        #    We ensure we don't cross the point-of-no-return between two steps.
        
        safety_buffer = (2.0 * overhead) + (5.0 * gap)
        panic_threshold = work_remaining + safety_buffer
        
        # Decision Logic
        if time_left < panic_threshold:
            # Panic Mode: We are too close to the deadline to risk waiting or Spot interruptions.
            # Use On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND
        else:
            # Normal Mode: We have slack. Prioritize cost savings.
            if has_spot:
                # Use Spot instances as they are significantly cheaper.
                return ClusterType.SPOT
            else:
                # Spot is unavailable, but we have enough time to wait.
                # Pausing (NONE) incurs no cost.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
