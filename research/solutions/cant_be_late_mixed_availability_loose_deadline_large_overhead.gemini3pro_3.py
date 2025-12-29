from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostOptimizedDeadlineAware"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        total_work = self.task_duration
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate progress
        # task_done_time is a list of durations of completed segments
        done_work = sum(self.task_done_time)
        remaining_work = total_work - done_work

        # If task is completed
        if remaining_work <= 0:
            return ClusterType.NONE

        time_until_deadline = deadline - elapsed

        # Safety Threshold Calculation
        # We must switch to On-Demand if the remaining time allows just enough 
        # to finish the work plus necessary overheads.
        # We add a safety buffer:
        # - 2 * overhead: Covers the transition cost to OD + margin
        # - 5 * gap: Handles discrete time step granularity and small delays
        safety_buffer = (2.0 * overhead) + (5.0 * gap)
        panic_threshold = remaining_work + safety_buffer

        # Panic Mode: Approaching the point of no return
        if time_until_deadline <= panic_threshold:
            return ClusterType.ON_DEMAND

        # Cost Optimization Mode:
        # Prioritize Spot instances (cheaper).
        # If Spot is unavailable, wait (NONE) rather than burning money on OD,
        # as long as we have slack (time_until_deadline > panic_threshold).
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)