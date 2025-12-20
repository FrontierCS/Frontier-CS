from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "RobustCostOptimizer"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done
        
        # If work is essentially done, stop
        if work_rem <= 1e-6:
            return ClusterType.NONE
            
        # Current time and parameters
        elapsed = self.env.elapsed_seconds
        time_rem = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Pricing estimates from problem description
        PRICE_OD = 3.06
        PRICE_SPOT = 0.97
        
        # Safety Check
        # We must ensure we have enough time to finish on On-Demand (the guaranteed resource).
        # The worst-case time required to finish on OD is:
        #   work_rem (time to do work) + overhead (time to restart/switch)
        # We add a buffer of 2 time steps to account for discrete step granularity.
        safe_time_needed = work_rem + overhead + (2.0 * gap)
        
        # If we are approaching the deadline such that we can barely finish on OD, 
        # we must switch to OD immediately to avoid failing the hard deadline.
        if time_rem <= safe_time_needed:
            return ClusterType.ON_DEMAND
            
        # Cost Optimization
        if has_spot:
            # Spot is available. 
            # If we are currently on OD, we should only switch if the savings justify the overhead.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Cost to finish on OD: remaining work * OD price
                cost_od = work_rem * PRICE_OD
                # Cost to finish on Spot: (remaining work + restart overhead) * Spot price
                # We include overhead in cost because it consumes instance time.
                cost_spot = (work_rem + overhead) * PRICE_SPOT
                
                if cost_spot < cost_od:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # If we are on Spot or None, and Spot is available, use it.
                return ClusterType.SPOT
        else:
            # Spot is unavailable.
            # Since we passed the safety check, we have sufficient slack.
            # We choose to wait (NONE) to save money, hoping Spot becomes available,
            # rather than spending on expensive OD immediately.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
