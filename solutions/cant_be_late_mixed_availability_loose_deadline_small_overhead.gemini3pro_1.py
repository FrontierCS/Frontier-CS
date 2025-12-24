import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        task_duration = self.task_duration
        overhead = self.restart_overhead
        
        # Calculate remaining work
        # task_done_time is a list of durations of completed segments
        done_work = sum(self.task_done_time)
        work_remaining = task_duration - done_work
        
        # If work is effectively done, stop
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        time_remaining = deadline - elapsed
        
        # Safety Logic ("Panic Mode"):
        # We must ensure we have enough time to finish the remaining work using On-Demand instances.
        # We assume the worst case: we might need to pay the restart overhead to switch/start OD.
        # We add a safety buffer of 2 * gap_seconds to account for the discrete time steps
        # and ensure we don't cross the point of no return between steps.
        
        safety_buffer = 2.0 * gap
        min_time_needed_od = work_remaining + overhead + safety_buffer
        
        # If we are within the danger zone, we must use On-Demand to guarantee completion.
        if time_remaining < min_time_needed_od:
            return ClusterType.ON_DEMAND
            
        # Cost Optimization Logic:
        # If we are not in danger (we have slack), we try to minimize cost.
        
        if has_spot:
            # Spot is significantly cheaper (~$0.97 vs ~$3.06), so use it if available.
            return ClusterType.SPOT
        else:
            # If Spot is unavailable but we still have slack, we choose NONE (wait).
            # This incurs $0 cost. Running OD here would be a waste of money since
            # we are not yet forced to do so by the deadline constraint.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
