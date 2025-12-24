from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostMinimizerStrategy"

    def __init__(self, args):
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Prefer Spot instances if available (lowest cost)
        if has_spot:
            return ClusterType.SPOT

        # 2. Calculate current progress and remaining work
        # task_done_time is a list of completed segment durations
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        work_remaining = self.task_duration - work_done

        # If work is effectively done, just pause (env should handle termination)
        if work_remaining <= 0:
            return ClusterType.NONE

        # 3. Time management
        time_now = self.env.elapsed_seconds
        time_remaining = self.deadline - time_now

        # Calculate slack time
        # We estimate time needed as remaining work + restart overhead
        # This overhead accounts for the time lost if we have to start an instance (OD or Spot)
        # Even if we are currently running, maintaining this buffer is safe
        time_needed = work_remaining + self.restart_overhead
        slack = time_remaining - time_needed

        # Define safety buffer
        # Ensure we switch to OD with enough margin to handle simulation step granularity
        # and avoid missing the hard deadline.
        # 1800s (30 mins) is conservative given the 70h deadline / 48h task (~22h slack).
        gap = getattr(self.env, "gap_seconds", 60.0)
        safety_buffer = max(1800.0, 3.0 * gap)

        # 4. Decision Logic for Spot Unavailable case
        
        # Critical Slack: Must use On-Demand to guarantee completion
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND

        # High Slack: Can afford to wait (NONE) to save money
        # Hysteresis optimization:
        # If we are currently running ON_DEMAND, only stop if we have enough slack
        # to justify the future restart overhead cost.
        # We avoid "micro-pauses" that cost more in overhead than they save in runtime.
        if last_cluster_type == ClusterType.ON_DEMAND:
            if slack > (safety_buffer + self.restart_overhead):
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
        
        # Default: Wait for Spot to return
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
