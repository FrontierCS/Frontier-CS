from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "HysteresisStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate timing and progress
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        duration = self.task_duration
        
        # Calculate work done: sum of completed segment durations
        work_done = sum(self.task_done_time)
        
        remaining_work = duration - work_done
        time_left = deadline - elapsed
        
        # Slack is the time budget we can afford to waste (idling or overhead)
        slack = time_left - remaining_work
        
        # Restart overhead in seconds
        R = self.restart_overhead
        
        # Threshold definitions:
        # 1. Safety Threshold
        # If slack falls below this, we are critically close to the deadline.
        # We must use ON_DEMAND to guarantee completion.
        # We include R because if we are not currently running/switching, we might pay R.
        # 1.1 multiplier adds a safety margin for step granularity.
        safety_threshold = R * 1.1
        
        # 2. Switch Threshold (Hysteresis)
        # To switch from ON_DEMAND to SPOT, we need enough slack to:
        # a) Absorb the restart overhead R (slack decreases by R during switch)
        # b) Remain above the safety_threshold after switching
        # c) Provide a buffer (300s) to prevent rapid oscillation if availability flutters
        switch_threshold = safety_threshold + R + 300.0

        # Decision Logic
        
        # If Spot is not available, we must use On-Demand.
        # Waiting (ClusterType.NONE) is too risky given the tight slack.
        if not has_spot:
            return ClusterType.ON_DEMAND
            
        # If Spot IS available, decide based on current state and slack
        if last_cluster_type == ClusterType.SPOT:
            # Currently on Spot: Maintain unless slack is critical
            if slack > safety_threshold:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
                
        elif last_cluster_type == ClusterType.ON_DEMAND:
            # Currently on OD: Switch to Spot only if we have excess slack
            # to justify the switching cost (overhead).
            if slack > switch_threshold:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
                
        else: # ClusterType.NONE (Initial state or resumed after pause)
            # Starting up: Both OD and Spot incur overhead R.
            # Prefer Spot if slack allows, with a small margin above safety.
            if slack > safety_threshold + 60.0:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)