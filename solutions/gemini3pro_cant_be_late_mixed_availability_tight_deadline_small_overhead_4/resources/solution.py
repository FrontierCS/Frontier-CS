from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLate_Optimized"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate time budget
        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        
        # Calculate time needed if we switch to On-Demand (OD) now.
        # If we are not currently running OD, we incur restart overhead to switch/start.
        overhead_penalty = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_penalty = self.restart_overhead
            
        time_needed_for_od = work_remaining + overhead_penalty
        
        # Define safety buffer to ensure we don't miss the deadline due to step granularity.
        # Use a fixed 15-minute buffer (900s) or 2x the step size, whichever is larger.
        step_gap = self.env.gap_seconds
        safety_buffer = max(900.0, 2.0 * step_gap)
        
        # CRITICAL CHECK:
        # If remaining time is close to the minimum time needed to finish on OD,
        # we must switch to OD immediately to guarantee completion.
        if time_left <= time_needed_for_od + safety_buffer:
            return ClusterType.ON_DEMAND
        
        # COST OPTIMIZATION:
        # If we have slack, prefer Spot instances as they are cheaper.
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable and we still have plenty of slack, wait (pause)
        # to avoid paying high OD costs, hoping Spot becomes available later.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
