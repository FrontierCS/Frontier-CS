import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "deadline_aware_greedy_v1"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide which cluster type to use based on deadline constraints and spot availability.
        """
        # Calculate remaining work
        completed_work = sum(self.task_done_time)
        work_remaining = self.task_duration - completed_work
        
        # Handle completion (floating point safety)
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        # Calculate time remaining until deadline
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        
        # Parameters
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Safety Buffer Calculation
        # We need enough time to:
        # 1. Complete the remaining work
        # 2. Pay the restart overhead (worst-case assumption: we might need to start fresh)
        # 3. Handle simulation step granularity and small variations
        # Buffer = 15 minutes (900s) + 2 simulation steps
        safety_buffer = 900.0 + (2.0 * gap)
        
        # Minimum time required to guarantee completion using On-Demand
        required_time_budget = work_remaining + overhead
        
        # Strategy Logic:
        # 1. Safety First: If we are close to the "Point of No Return", switch to reliable On-Demand.
        #    The Point of No Return is when Time Remaining equals Work Needed + Overhead.
        if time_remaining < (required_time_budget + safety_buffer):
            return ClusterType.ON_DEMAND
            
        # 2. Cost Optimization: If we have slack (safety buffer not breached), prefer Spot.
        if has_spot:
            return ClusterType.SPOT
        
        # 3. Slack Utilization: If Spot is unavailable but we have slack, wait (NONE).
        #    This burns slack (time) to save money, hoping Spot returns before the buffer is hit.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)