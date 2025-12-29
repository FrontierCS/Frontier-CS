import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment state (all units in seconds)
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate remaining work
        # self.task_done_time is a list of completed segment durations
        done = sum(self.task_done_time)
        total = self.task_duration
        remaining_work = max(0.0, total - done)
        
        # If work is completed, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE
            
        remaining_time = deadline - elapsed
        
        # Define a safety buffer (2 time steps) to handle simulation granularity
        buffer = 2.0 * gap
        
        # Calculate the critical threshold.
        # We must ensure that T_rem >= W_rem + Overhead + Buffer.
        # The overhead is included to account for the cost of starting an OD instance
        # if we are not currently on one, or simply as a safety margin against flapping.
        threshold = remaining_work + overhead + buffer
        
        # Criticality check: If we are running out of time, force On-Demand usage.
        if remaining_time <= threshold:
            return ClusterType.ON_DEMAND
            
        # If we have sufficient slack, prioritize cost optimization.
        if has_spot:
            # Use Spot instances when available (cheapest option)
            return ClusterType.SPOT
        else:
            # If Spot is unavailable but we have slack, wait (pause) 
            # to avoid paying high On-Demand costs unnecessarily.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)