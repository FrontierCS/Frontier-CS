from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def __init__(self, args):
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Current state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        
        # Calculate progress
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        remaining_time = deadline - elapsed
        slack = remaining_time - remaining_work
        
        # Panic Threshold:
        # We need at least 'overhead' time to start/restart an instance.
        # We add a safety buffer of 4 simulation steps to handle granularity.
        # If slack falls below this, we must use On-Demand to guarantee the deadline.
        panic_threshold = overhead + (4.0 * gap)
        
        if slack < panic_threshold:
            return ClusterType.ON_DEMAND
            
        if has_spot:
            # Spot is available and we have slack.
            # Optimization: If we are currently on OD and the remaining work is very short,
            # switching to Spot might be more expensive due to the restart overhead cost.
            # Heuristic: stay on OD if remaining work < 0.5 * overhead.
            if last_cluster_type == ClusterType.ON_DEMAND and remaining_work < (overhead * 0.5):
                return ClusterType.ON_DEMAND
                
            return ClusterType.SPOT
        else:
            # No Spot available, but we have plenty of slack.
            # Wait (NONE) to save money.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)