from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve current state variables
        elapsed_seconds = self.env.elapsed_seconds
        gap_seconds = self.env.gap_seconds
        
        # Calculate remaining work
        # task_done_time is a list of durations (seconds) of completed segments
        total_work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_work_done
        
        # If the task is effectively complete, stop incurring costs
        if remaining_work <= 1e-6:
            return ClusterType.NONE
            
        # Calculate time remaining until the hard deadline
        time_remaining = self.deadline - elapsed_seconds
        
        # Calculate the time required to finish if we switch to (or continue) On-Demand NOW.
        # If we are not currently running On-Demand, we incur a restart overhead.
        # If we are already running On-Demand, we continue without additional overhead.
        overhead_penalty = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_penalty = self.restart_overhead
            
        time_needed_for_od = remaining_work + overhead_penalty
        
        # Define a safety buffer.
        # We need to account for the discrete time step (gap_seconds).
        # If we wait this step (NONE or failed SPOT), time_remaining decreases by gap_seconds.
        # We must ensure we switch to OD *before* time_remaining < time_needed_for_od.
        # A buffer of 2 steps covers the current step decision and potential floating point margins.
        safety_buffer = 2.0 * gap_seconds
        
        # CRITICAL DEADLINE CHECK:
        # If remaining time is close to the minimum time needed for OD, we MUST use OD.
        # This acts as the "panic threshold" to ensure we never miss the deadline.
        if time_remaining <= time_needed_for_od + safety_buffer:
            return ClusterType.ON_DEMAND
            
        # COST OPTIMIZATION:
        # If we have slack (not near the deadline threshold):
        # 1. Prefer Spot instances because they are significantly cheaper (~1/3 cost).
        if has_spot:
            return ClusterType.SPOT
            
        # 2. If Spot is unavailable, wait (NONE).
        # Using OD now would waste money since we have slack to wait for Spot to return.
        # We only burn slack time here, which is free (cost = 0).
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)