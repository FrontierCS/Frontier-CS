from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "SlackBasedGreedyStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate accumulated work and remaining requirements
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Slack is the time budget we can waste (waiting or restart overheads) 
        # while still finishing on time using On-Demand (which has 1:1 progress).
        slack = time_remaining - work_remaining
        
        # We must switch to On-Demand if the slack drops near the cost of switching.
        # Switching to any instance (including OD) incurs restart_overhead.
        # We add a safety buffer of 2 time steps to account for discrete step timing.
        # If slack < threshold, we cannot afford to wait or risk a Spot preemption/restart.
        threshold = self.restart_overhead + (2.0 * self.env.gap_seconds)
        
        if slack < threshold:
            return ClusterType.ON_DEMAND
            
        if has_spot:
            return ClusterType.SPOT
            
        # If we have slack but no Spot is available, wait (NONE) to save money
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)