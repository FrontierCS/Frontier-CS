from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate total work done so far
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If the task is already completed, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # Calculate time remaining until the hard deadline
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Calculate the time required to finish the task using On-Demand instances.
        # If we are currently running On-Demand, we can continue without overhead.
        # If we are running Spot or paused (NONE), switching to On-Demand incurs a restart overhead.
        switch_overhead = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_overhead = self.restart_overhead
            
        time_needed_od = remaining_work + switch_overhead
        
        # Define a safety buffer to ensure we switch to On-Demand before it's too late.
        # We include:
        # 1. A fixed margin (1200s = 20 mins) to account for potential variance and high penalty risk.
        # 2. Twice the step size (gap_seconds) to ensure the decision logic holds across the current time step.
        safety_buffer = 1200.0 + (2.0 * self.env.gap_seconds)
        
        # If the remaining time is close to the minimum time needed on On-Demand, 
        # force the use of On-Demand to guarantee meeting the deadline.
        if time_remaining < time_needed_od + safety_buffer:
            return ClusterType.ON_DEMAND
            
        # If we have sufficient slack, prefer Spot instances to minimize cost.
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable but we have plenty of time, wait (pause) to save money.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)