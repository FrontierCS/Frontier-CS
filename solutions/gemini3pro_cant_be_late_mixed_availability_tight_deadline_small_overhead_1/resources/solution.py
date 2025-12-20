from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "RobustDeadlineOptimizer"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate total work completed so far
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If the task is already completed, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE
            
        elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed
        
        # Calculate overhead required if we were to switch to On-Demand now.
        # If we are already on On-Demand, no new overhead is incurred.
        # If we are on Spot or None, we would pay restart_overhead to switch.
        overhead_cost = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_cost = self.restart_overhead
            
        # Determine the "Panic Threshold".
        # We must ensure that we switch to On-Demand while we still have enough time 
        # to complete the work plus any startup overheads.
        # We add a safety buffer to account for:
        # 1. The discrete time step (gap_seconds): If we wait now, we lose this much time.
        # 2. General robustness: To prevent missing the hard deadline due to floating point variations.
        safety_buffer = self.restart_overhead + 2.0 * self.env.gap_seconds
        
        must_start_od_threshold = work_remaining + overhead_cost + safety_buffer
        
        # Critical Logic: If we are close to the point of no return, force On-Demand.
        if time_remaining <= must_start_od_threshold:
            return ClusterType.ON_DEMAND
            
        # Standard Logic: If we have slack, prioritize cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable, but we have enough slack to wait and save money.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
