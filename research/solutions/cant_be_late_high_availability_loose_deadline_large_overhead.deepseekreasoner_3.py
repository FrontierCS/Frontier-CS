import argparse
import math
from typing import List, Tuple

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.price_ratio = self.spot_price / self.ondemand_price
        self.min_safety_buffer = 2.0 * 3600  # 2 hours minimum safety buffer

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        time_step = self.env.gap_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        
        # Calculate total work done so far
        total_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - total_done
        
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # Calculate time remaining until deadline
        time_remaining = deadline - elapsed
        
        # Calculate conservative completion time estimates
        spot_time_needed = work_remaining + restart_overhead
        ondemand_time_needed = work_remaining
        
        # Safety factors based on time remaining
        critical_threshold = 4.0 * 3600  # 4 hours
        moderate_threshold = 12.0 * 3600  # 12 hours
        
        if time_remaining <= critical_threshold:
            # Critical zone - must use on-demand to guarantee completion
            return ClusterType.ON_DEMAND if has_spot else ClusterType.ON_DEMAND
        
        # Calculate effective work rate
        if has_spot:
            # Estimate effective work rate for spot considering availability
            # Conservative estimate: assume 60% availability
            effective_spot_rate = 0.6
            spot_effective_time = work_remaining / effective_spot_rate + restart_overhead
            
            # Check if we can afford spot risk
            safety_margin = max(self.min_safety_buffer, 0.2 * time_remaining)
            
            if spot_effective_time + safety_margin <= time_remaining:
                # We have enough buffer to use spot
                # Only use spot if it's significantly cheaper considering risks
                risk_adjusted_cost = self.spot_price / effective_spot_rate
                if risk_adjusted_cost < self.ondemand_price * 0.7:  # 30% cheaper
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # Not enough buffer for spot
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            if time_remaining <= moderate_threshold:
                # Getting close to deadline, use on-demand
                return ClusterType.ON_DEMAND
            else:
                # We have time, wait for spot to become available
                # But only if we have significant buffer
                wait_buffer = 6.0 * 3600  # 6 hours buffer to wait
                if time_remaining - ondemand_time_needed > wait_buffer:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)