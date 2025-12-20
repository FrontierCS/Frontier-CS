from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import math

class Solution(Strategy):
    NAME = "SafeSlackConsumer"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Calculate work status
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # 2. Calculate time status
        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        
        # 3. Define Safety Threshold
        # We calculate the "Panic Point": the latest possible moment to switch to On-Demand
        # to guarantee finishing the task, assuming we incur a restart overhead.
        
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Buffer calculation:
        # - overhead * 1.1: Accounts for the restart time needed to spin up OD, plus 10% safety margin.
        # - gap * 2.0: Ensures we don't overshoot the deadline due to step granularity.
        # We must ensure that even if we wait one full 'gap' (waiting for this step to end),
        # we still have enough time (remaining_work + overhead) to finish.
        safety_buffer = (overhead * 1.1) + (gap * 2.0)
        
        required_time_for_od = remaining_work + overhead + safety_buffer
        
        # 4. Decision Logic
        
        # Priority 1: Guarantee Deadline
        # If we are approaching the point of no return, force On-Demand.
        if time_left < required_time_for_od:
            return ClusterType.ON_DEMAND
            
        # Priority 2: Minimize Cost using Slack
        # If we have buffer time:
        if has_spot:
            # If Spot is available, use it (cheapest option).
            # Even if we switch from OD to Spot, the savings usually outweigh the overhead 
            # given the ~3x price difference and long task duration.
            return ClusterType.SPOT
        else:
            # If Spot is unavailable but we still have buffer time:
            # Wait (NONE). This consumes slack but costs $0.
            # We bet on Spot coming back before we hit the panic threshold.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
