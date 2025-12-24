from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work and time
        # self.task_done_time is a list of completed work segments
        work_done = sum(self.task_done_time)
        work_rem = max(0.0, self.task_duration - work_done)
        time_rem = self.deadline - self.env.elapsed_seconds
        
        # Calculate slack: the amount of time we can afford to waste (wait or restart)
        # without missing the deadline.
        # Slack = (Time Remaining) - (Work Remaining)
        slack = time_rem - work_rem
        
        # Define Safety Threshold
        # We must switch to On-Demand if the slack drops too low.
        # The absolute minimum buffer needed is 'restart_overhead' (time to start the OD instance).
        # We add a safety margin (10 minutes + 2 timesteps) to account for:
        # 1. Simulation step granularity (gap_seconds)
        # 2. Potential lags in task progress reporting
        # 3. Robustness against floating point issues
        margin = 600 + (2 * self.env.gap_seconds)
        panic_threshold = self.restart_overhead + margin
        
        # Decision Logic
        
        # 1. Panic Mode: If slack is critically low, we must use On-Demand.
        # Even if Spot is available, the risk of interruption (and subsequent restart overhead)
        # could cause us to miss the deadline. On-Demand guarantees completion.
        if slack < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Economy Mode: If we have sufficient slack, prioritize cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable, but we have a healthy slack buffer.
            # Instead of paying for expensive On-Demand immediately, we wait (NONE).
            # This consumes slack (time passes, work doesn't), but saves money.
            # If Spot doesn't become available, slack will eventually drop to the 
            # panic_threshold, forcing a switch to On-Demand.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
