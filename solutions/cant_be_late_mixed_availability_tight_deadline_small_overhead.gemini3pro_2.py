import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize state variables for the evaluation run.
        """
        self.last_done_sum = 0.0
        self.current_run_time = 0.0
        self.running_type = ClusterType.NONE
        self.prev_cluster_type = ClusterType.NONE
        # Safety buffer: 1800 seconds (30 minutes)
        # This provides a margin for the safety check to switch to On-Demand
        # before the deadline becomes impossible to meet.
        self.safety_buffer = 1800.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide the next cluster type based on current state and safety constraints.
        """
        # 1. Update Progress Tracking
        # Check if the environment has settled any new segments into task_done_time
        current_done_sum = sum(self.task_done_time)
        if current_done_sum > self.last_done_sum + 1e-6:
            # A segment finished or settled (e.g., due to interruption or completion)
            # Reset current continuous run tracking
            self.current_run_time = 0.0
            self.last_done_sum = current_done_sum

        # Update current run duration based on what happened in the last step
        if last_cluster_type == ClusterType.NONE:
            self.current_run_time = 0.0
            self.running_type = ClusterType.NONE
        else:
            # If the cluster type matches what we saw previously, it's a continuation
            if last_cluster_type == self.prev_cluster_type:
                self.current_run_time += self.env.gap_seconds
            else:
                # Type changed (Switch or Start), reset timer to the duration of this step
                self.running_type = last_cluster_type
                self.current_run_time = self.env.gap_seconds
        
        # Store the current last_cluster_type for the next step comparison
        self.prev_cluster_type = last_cluster_type

        # 2. Estimate Effective Work Done
        # Calculate pending work from the current running instance (subtracting overhead)
        # We assume progress accumulates but requires 'restart_overhead' to effectively start.
        pending_work = max(0.0, self.current_run_time - self.restart_overhead)
        total_estimated_done = current_done_sum + pending_work
        
        # Calculate remaining work and time
        work_remaining = max(0.0, self.task_duration - total_estimated_done)
        time_left = self.deadline - self.env.elapsed_seconds
        
        # 3. Decision Logic
        # Calculate time needed to finish if we use On-Demand (worst case scenario)
        # We add restart_overhead conservatively to ensure we can restart on OD if needed.
        time_needed_od = work_remaining + self.restart_overhead
        
        # Safety Check: If we are close to the point of no return, force On-Demand.
        if time_left < (time_needed_od + self.safety_buffer):
            return ClusterType.ON_DEMAND
        
        # If we are safe, prefer Spot instances to save cost
        if has_spot:
            return ClusterType.SPOT
        
        # If no Spot is available but we have slack, wait (NONE) to save money
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
