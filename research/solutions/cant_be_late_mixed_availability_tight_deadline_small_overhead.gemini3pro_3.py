from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate current progress
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If task is completed, stop
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate time parameters
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_remaining = deadline - elapsed
        
        # Calculate Slack: The buffer of time we can afford to waste (waiting or overhead)
        # If we used OD immediately and continuously, we would finish in 'work_remaining' + 'overhead' (if switching).
        slack = time_remaining - work_remaining
        
        # Determine Safety Threshold
        # We need to guarantee that if we switch to On-Demand, we have enough time to finish.
        # Minimum required slack = Restart Overhead + Safety Buffer
        # Safety Buffer includes:
        # 1. The current time step duration (gap), as we might wait this step.
        # 2. A constant margin (10 minutes = 600s) to be robust against variations.
        restart_overhead = self.restart_overhead
        gap = self.env.gap_seconds
        threshold = restart_overhead + gap + 600.0
        
        # Decision Logic
        
        # 1. Panic Mode: Slack is low. We must use On-Demand to guarantee deadline.
        if slack < threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Normal Mode: We have sufficient slack. Optimize for cost.
        if has_spot:
            # Spot is available. Use it to save money.
            # Even if we are currently on OD, switching to Spot (paying overhead) is worth it
            # given the significant cost difference and ample slack.
            return ClusterType.SPOT
        else:
            # Spot is unavailable. Since we have slack, wait (NONE) to save OD costs.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)