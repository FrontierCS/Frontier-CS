from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def __init__(self, args):
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work based on completed segments
        done_work = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done_work)
        
        # If the task is effectively complete, stop incurring costs
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Current status
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        gap = self.env.gap_seconds

        # Calculate Safety Threshold for Panic Mode
        # We must switch to On-Demand (OD) if we are approaching the point where 
        # completion is at risk. OD is reliable but expensive.
        #
        # Required Time Calculation:
        # 1. remaining_work: Actual compute time needed.
        # 2. restart_overhead: Time to spin up the OD instance.
        # 3. Buffer: Safety margin for discrete time steps, simulation jitter, 
        #    and to ensure we don't cut it too close.
        #
        # Buffer choice: 
        # - 1x restart_overhead (0.2h) to allow for safe switching
        # - 3600s (1h) constant cushion (Given 22h slack, this cost is negligible for safety)
        # - 2x gap_seconds to handle step boundaries
        
        safety_buffer = self.restart_overhead + 3600.0 + (2.0 * gap)
        
        # Total time required to guarantee finish on OD
        required_time_on_od = remaining_work + self.restart_overhead + safety_buffer

        # Decision Logic:
        # 1. Panic Mode: If time is running out, force OD immediately.
        if time_remaining < required_time_on_od:
            return ClusterType.ON_DEMAND

        # 2. Standard Mode:
        # - If Spot is available, use it (cheapest option).
        # - If Spot is unavailable, wait (ClusterType.NONE).
        #   Waiting is free, whereas running OD is expensive. Since we are not in 
        #   Panic Mode, we have slack to burn in exchange for cost savings.
        if has_spot:
            return ClusterType.SPOT
        
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
