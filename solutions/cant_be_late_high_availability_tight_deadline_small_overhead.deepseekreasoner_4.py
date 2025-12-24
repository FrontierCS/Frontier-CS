from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import math

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        time_per_step = self.env.gap_seconds
        
        # If no work remaining, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # Calculate effective work per step considering restart overhead
        effective_work_per_step = time_per_step
        if last_cluster_type == ClusterType.NONE:
            effective_work_per_step = max(0, time_per_step - self.restart_overhead)
        
        # Calculate minimum steps needed (pessimistic)
        min_steps_needed = math.ceil(work_remaining / effective_work_per_step)
        
        # Calculate safety threshold - when to switch to on-demand
        # Use aggressive spot usage when plenty of time
        safety_margin = self.restart_overhead * 3  # 3 restart cycles as buffer
        
        # If we're in a tight situation, use on-demand
        if time_remaining <= work_remaining + safety_margin:
            if last_cluster_type != ClusterType.ON_DEMAND:
                # Starting on-demand incurs restart overhead
                return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # If spot is available and we have time, use it
        if has_spot:
            # Avoid frequent switching by continuing with current type if possible
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            # Only switch to spot if we gain enough benefit
            spot_time_needed = work_remaining / time_per_step
            od_time_needed = work_remaining / time_per_step
            
            # Factor in restart overhead for switching
            if last_cluster_type != ClusterType.NONE:
                spot_time_needed += self.restart_overhead / time_per_step
            
            # Use spot if it saves significant time
            if spot_time_needed < od_time_needed * 0.7:  # Spot must be 30% faster
                return ClusterType.SPOT
            return last_cluster_type
        
        # If no spot available, continue with current or pause
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND
        
        # If we were on spot and lost it, pause to wait for spot return
        # but only if we have time
        wait_threshold = 10  # steps to wait for spot
        time_to_wait = wait_threshold * time_per_step
        if time_remaining > work_remaining + time_to_wait + safety_margin:
            return ClusterType.NONE
        
        # Otherwise, switch to on-demand
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
