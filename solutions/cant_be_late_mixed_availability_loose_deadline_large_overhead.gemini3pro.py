from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "SafeSlackStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment parameters
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        total_duration = self.task_duration
        work_done = sum(self.task_done_time)
        restart_overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate remaining time and work
        remaining_time = deadline - elapsed
        remaining_work = total_duration - work_done
        
        # Calculate slack: the amount of time we can afford to not make progress
        # If slack is 0, we must run continuously on a resource that guarantees progress.
        slack = remaining_time - remaining_work
        
        # Define safety margin
        # We need to switch to On-Demand before slack runs out.
        # We add a buffer of 3600s (1 hour) plus 2 timesteps to handle granularity and safety.
        # The penalty for missing the deadline is severe, so we prioritize safety over squeeze.
        safety_buffer = 3600.0 + (2.0 * gap)
        
        # Determine the time cost required to switch to On-Demand
        # If we are already running On-Demand, there is no switch cost (overhead).
        # Otherwise (Spot or None), we must pay the restart overhead to start OD.
        time_to_start_od = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            time_to_start_od = restart_overhead
            
        # Critical threshold: If slack drops below this, we must use On-Demand immediately.
        threshold = time_to_start_od + safety_buffer
        
        # Decision Logic
        if slack < threshold:
            # We are close to the deadline relative to our buffer.
            # Must use On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND
            
        if has_spot:
            # We have sufficient slack and Spot is available.
            # Use Spot to minimize cost.
            return ClusterType.SPOT
            
        # Spot is unavailable, but we have enough slack to wait.
        # Waiting (NONE) costs $0, preserving budget.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
