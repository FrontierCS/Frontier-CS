import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        time_left = self.deadline - self.env.elapsed_seconds
        
        # If work is done, stop everything
        if work_left <= 0:
            return ClusterType.NONE
        
        # Calculate safe thresholds
        # Minimum time needed if using only on-demand
        min_time_needed = work_left
        if last_cluster_type == ClusterType.NONE:
            min_time_needed += self.restart_overhead
        
        # Calculate risk factor based on time pressure
        time_pressure = max(0, min_time_needed / time_left if time_left > 0 else float('inf'))
        
        # Determine current mode
        # Mode 0: Aggressive (use spot whenever available)
        # Mode 1: Conservative (use on-demand when time is tight)
        # Mode 2: Emergency (only on-demand)
        
        if time_pressure > 0.9 or time_left < min_time_needed * 1.1:
            mode = 2  # Emergency mode
        elif time_pressure > 0.7 or time_left < min_time_needed * 1.3:
            mode = 1  # Conservative mode
        else:
            mode = 0  # Aggressive mode
        
        # Handle restart overhead consideration
        in_restart = (last_cluster_type == ClusterType.NONE and 
                     self.env.elapsed_seconds < getattr(self, '_restart_end', 0))
        
        # Update restart tracking
        if (last_cluster_type != ClusterType.NONE and 
            self.env.cluster_type == ClusterType.NONE):
            self._restart_end = self.env.elapsed_seconds + self.restart_overhead
        
        # Decision logic
        if mode == 0:  # Aggressive
            if has_spot and not in_restart:
                return ClusterType.SPOT
            elif in_restart:
                return ClusterType.NONE
            else:
                # Wait for spot if we have time
                wait_penalty = self.restart_overhead if last_cluster_type == ClusterType.NONE else 0
                safe_wait_time = time_left - (work_left + wait_penalty)
                if safe_wait_time > 3600:  # Can wait up to 1 hour
                    return ClusterType.NONE
                return ClusterType.ON_DEMAND
                
        elif mode == 1:  # Conservative
            if has_spot and not in_restart and work_left > 7200:  # More than 2 hours left
                # Use spot but with safety margin
                spot_safe = time_left > (work_left + self.restart_overhead) * 1.5
                if spot_safe:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            elif in_restart:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
                
        else:  # Emergency mode
            if in_restart:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)