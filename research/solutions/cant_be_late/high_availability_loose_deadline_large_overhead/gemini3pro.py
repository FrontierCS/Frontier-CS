from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - elapsed
        
        # Slack represents the amount of time we can afford to not make progress
        # (due to waiting for Spot or incurring restart overheads)
        slack = remaining_time - remaining_work
        
        # Safety buffer to guarantee completion.
        # We need to switch to On-Demand before slack runs out.
        # Restart overhead is 720s (0.2h). 
        # A buffer of 3600s (1h) is conservative enough to absorb overheads 
        # and ensure we meet the deadline even if we switch late.
        # Given 22h total slack, 1h buffer has minimal impact on cost efficiency.
        SAFETY_BUFFER = 3600.0
        
        if slack < SAFETY_BUFFER:
            return ClusterType.ON_DEMAND
            
        if has_spot:
            return ClusterType.SPOT
            
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)