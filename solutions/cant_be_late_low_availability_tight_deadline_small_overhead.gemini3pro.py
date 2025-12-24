import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        
        if work_left <= 0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        
        # Safety Logic:
        # We must ensure that if we choose to delay using On-Demand (by picking SPOT or NONE),
        # and that choice results in zero progress for this step, we can still finish 
        # the remaining work using On-Demand starting from the NEXT step.
        #
        # Switching to or starting On-Demand incurs a restart overhead.
        #
        # Variables at start of next step (if this step yields 0 progress):
        #   Next Time Left = time_left - gap
        #   Work Left = work_left
        #   Time Needed on OD = work_left + overhead
        #
        # Constraint: Next Time Left >= Time Needed on OD + buffer
        
        safety_buffer = gap * 0.1  # Safety margin for floating point/timing jitter
        min_time_needed_next = work_left + overhead + safety_buffer
        time_available_next = time_left - gap
        
        if time_available_next < min_time_needed_next:
            # We are running out of slack. Must use reliable On-Demand.
            return ClusterType.ON_DEMAND
            
        # If we have sufficient slack:
        if has_spot:
            # Prioritize Spot for cost savings
            return ClusterType.SPOT
        else:
            # If Spot unavailable but slack exists, wait (NONE).
            # Waiting is free; running OD is expensive. 
            # Waiting preserves the option to use Spot later.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
