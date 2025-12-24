from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "AdaptiveThresholdStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve current state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        duration = self.task_duration
        done_work = sum(self.task_done_time)
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Calculate remaining requirements
        work_remaining = duration - done_work
        time_remaining = deadline - elapsed
        
        # Slack is the amount of time we can afford to waste (wait or restart)
        # before we must run continuously to meet the deadline.
        slack = time_remaining - work_remaining

        # Safety Threshold:
        # We must switch to On-Demand if slack gets dangerously low.
        # We need enough buffer to cover the restart overhead (if we are currently
        # paused or need to switch types) plus some margin for time step granularity.
        # 3.0x overhead + 2.0x gap is a conservative safety margin.
        safety_threshold = 3.0 * overhead + 2.0 * gap

        # 1. Panic Logic:
        # If slack is below the threshold, we risk missing the deadline.
        # Switch to On-Demand immediately to guarantee progress.
        if slack < safety_threshold:
            return ClusterType.ON_DEMAND

        # 2. Spot Availability Logic:
        if has_spot:
            # Hysteresis Check:
            # If we are currently on On-Demand (likely due to previous low slack or
            # lack of Spot), switching to Spot incurs a restart overhead.
            # This overhead consumes slack. We should only switch if the remaining
            # slack *after* the switch is still comfortably above the safety threshold.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if slack > safety_threshold + overhead + gap:
                    return ClusterType.SPOT
                else:
                    # Not enough buffer to pay the switch cost; stay safe on OD.
                    return ClusterType.ON_DEMAND
            
            # If we are not on OD (e.g., NONE or SPOT), and Spot is available, use it.
            return ClusterType.SPOT

        # 3. Wait Logic:
        # If Spot is unavailable but we have plenty of slack, it is cheaper to 
        # wait (return NONE) than to burn money on On-Demand.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
