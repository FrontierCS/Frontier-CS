from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "Lazy_Slack_Reservation"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work (seconds)
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        
        # Check if task is effectively finished
        if remaining_work <= 1e-4:
            return ClusterType.NONE
            
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        # Calculate Real Slack: The amount of time we can afford to not make progress.
        # This includes time spent Waiting (NONE) and time spent on Restart Overheads.
        real_slack = time_left - remaining_work
        
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Safety Threshold Calculation:
        # We must switch to On-Demand before our slack becomes insufficient to cover
        # the restart overhead required to start the On-Demand instance.
        # We add a safety margin of 2 * gap to account for discrete time steps.
        # If slack < overhead, we would fail if we are currently stopped.
        safety_threshold = overhead + (2.0 * gap)
        
        # Critical Phase: If slack is running out, force On-Demand.
        # We prioritize reliability here to avoid the -100,000 penalty.
        # Switching to OD ensures we finish on time even if it costs more.
        if real_slack < safety_threshold:
            return ClusterType.ON_DEMAND
            
        # Opportunistic Phase: If we have sufficient slack, prefer Spot.
        if has_spot:
            return ClusterType.SPOT
            
        # If no Spot and sufficient slack, Wait (NONE).
        # This delays execution ("Least Laxity First") to maximize the chance
        # of overlapping with future Spot availability windows, reducing total cost.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)