from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import math
import time

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        completed = sum(self.task_done_time) if self.task_done_time else 0
        remaining_work = self.task_duration - completed
        
        # Calculate time remaining until deadline
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Emergency mode: if we're running out of time, use on-demand
        # We need enough time to finish work plus potential restart overhead
        safe_threshold = remaining_work + self.restart_overhead * 2
        if time_remaining <= safe_threshold:
            return ClusterType.ON_DEMAND
        
        # If spot is available and we have time, use spot
        if has_spot:
            # Calculate progress rate - we need to ensure we're making progress
            if remaining_work > 0:
                # Estimate required progress rate
                required_rate = remaining_work / time_remaining
                
                # If we're making insufficient progress, switch to on-demand
                if required_rate > 0.9:  # 90% utilization required
                    return ClusterType.ON_DEMAND
            
            # Use spot if available
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.NONE:
                # Only start spot if we have enough buffer
                buffer_needed = self.restart_overhead * 3
                if time_remaining - remaining_work > buffer_needed:
                    return ClusterType.SPOT
                else:
                    return ClusterType.NONE
            else:  # Coming from on-demand
                # Stay on on-demand if we recently switched
                time_since_switch = self.env.elapsed_seconds - (self.task_done_time[-1] if self.task_done_time else 0)
                if time_since_switch < self.restart_overhead * 2:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.SPOT
        
        # Spot not available
        if last_cluster_type == ClusterType.SPOT:
            # We just lost spot - decide whether to switch to on-demand or pause
            if time_remaining <= remaining_work + self.restart_overhead * 1.5:
                return ClusterType.ON_DEMAND
            else:
                # Pause and wait for spot to return
                return ClusterType.NONE
        elif last_cluster_type == ClusterType.ON_DEMAND:
            # Stay on on-demand if we're using it
            return ClusterType.ON_DEMAND
        else:  # NONE
            # Decide whether to start on-demand or continue waiting
            if time_remaining <= remaining_work + self.restart_overhead * 2:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)