from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment status
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Calculate work progress
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - work_done)
        
        # If work is completed, stop using resources
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_remaining = self.deadline - elapsed

        # Calculate effective overhead if we switch to/continue On-Demand
        # If we are already running OD, we assume no new restart overhead
        if last_cluster_type == ClusterType.ON_DEMAND:
            effective_overhead = 0.0
        else:
            effective_overhead = self.restart_overhead

        # Determine safety buffer
        # We need a buffer to handle step granularity (gap) and a safety margin
        # 900s (15 min) + 2 * gap is conservative to prevent deadline misses
        safety_buffer = 900.0 + (2.0 * gap)

        # Calculate time required to finish using On-Demand
        time_needed_od = work_remaining + effective_overhead + safety_buffer

        # Panic Logic: If we are close to the deadline threshold, force On-Demand
        if time_remaining <= time_needed_od:
            return ClusterType.ON_DEMAND

        # Economy Logic: If we have slack
        if has_spot:
            # Use Spot if available (cheapest option)
            return ClusterType.SPOT
        else:
            # If Spot is unavailable and we have slack, wait (cost = 0)
            # This avoids paying for On-Demand when not strictly necessary
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
