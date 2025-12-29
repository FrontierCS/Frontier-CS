import argparse
from typing import List

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "DeadlineAwareStrategy"

    def __init__(self, args):
        super().__init__()
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        
        # Calculate work remaining
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If task is complete (defensive check)
        if work_remaining <= 0:
            return ClusterType.NONE

        time_remaining = deadline - elapsed

        # Calculate the time required to finish if we commit to On-Demand immediately.
        # If we are already running On-Demand, we assume no new restart overhead is needed
        # (unless we were interrupted, but last_cluster_type tracks our intent).
        # If we are on Spot or None, switching to On-Demand incurs the restart overhead.
        time_needed_on_demand = work_remaining
        if last_cluster_type != ClusterType.ON_DEMAND:
            time_needed_on_demand += restart_overhead

        # Safety buffer: ensure we switch with enough time margin.
        # We use 2 time steps (gap) plus a small constant to handle discrete time boundaries safely.
        # This prevents overshooting the deadline due to step granularity.
        safety_buffer = 2.0 * gap + 1.0

        # Critical Deadline Check:
        # If the remaining time is close to the bare minimum needed for On-Demand execution,
        # we must switch to (or stay on) On-Demand to guarantee completion.
        if time_remaining < (time_needed_on_demand + safety_buffer):
            return ClusterType.ON_DEMAND

        # If we have sufficient slack time:
        if has_spot:
            # Use Spot instances to minimize cost
            return ClusterType.SPOT
        else:
            # If Spot is unavailable but we still have slack, wait (NONE) to save money
            # rather than burning expensive On-Demand hours unnecessarily.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)