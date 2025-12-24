import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def solve(self, spec_path: str) -> "Solution":
        # Read configuration if needed
        # spec_path contains additional configuration parameters
        # No additional setup needed for this implementation
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - work_done)
        remaining_time = max(0.0, self.deadline - self.env.elapsed_seconds)
        
        # Calculate the effective work needed considering restart overhead
        # If we're currently running and have to restart, we'll lose restart_overhead time
        effective_remaining_work = remaining_work
        
        # If we're not currently running (NONE or just preempted), we need restart time
        if last_cluster_type == ClusterType.NONE:
            effective_remaining_work += self.restart_overhead
        
        # Calculate minimum time needed if using only on-demand
        min_time_needed = effective_remaining_work
        
        # If we're in critical state (not enough time even for on-demand), use on-demand
        if remaining_time <= min_time_needed + self.env.gap_seconds * 2:
            return ClusterType.ON_DEMAND
        
        # Calculate how much slack we have
        slack = remaining_time - min_time_needed
        
        # Define safety thresholds based on slack
        # When slack is large, we can take more risks with spot
        # When slack is small, we must be conservative
        
        # Conservative threshold: switch to on-demand when slack < threshold
        # Use exponential decay for risk tolerance
        risk_factor = min(1.0, slack / (self.restart_overhead * 10))
        
        # Use spot when available and we have sufficient risk tolerance
        if has_spot and risk_factor > 0.3:
            # Occasionally pause to avoid continuous spot usage during low slack
            # This helps save cost while maintaining progress
            if risk_factor < 0.5 and last_cluster_type == ClusterType.SPOT:
                # Small chance to pause when risk is moderate
                # This creates breaks that can be used to reassess
                if work_done / self.task_duration > 0.8:  # Near completion
                    return ClusterType.SPOT
                return ClusterType.NONE
            return ClusterType.SPOT
        elif not has_spot:
            # When spot is not available, decide between on-demand and pause
            if risk_factor < 0.4:
                return ClusterType.ON_DEMAND
            else:
                # Pause to wait for spot availability when we have time
                return ClusterType.NONE
        else:
            # Has spot but risk is too low
            if risk_factor < 0.2:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
