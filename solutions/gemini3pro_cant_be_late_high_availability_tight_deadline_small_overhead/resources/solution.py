from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "AdaptiveSlackStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate total work completed so far
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # Calculate current slack (time buffer)
        # Slack is the amount of time we can afford to waste (wait or restart overhead)
        time_left = self.deadline - self.env.elapsed_seconds
        slack = time_left - remaining_work
        
        # Environment parameters
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Safety margin to account for discrete time steps
        safety_margin = 2.0 * gap
        
        # Determine the threshold where we MUST use On-Demand to guarantee completion.
        # If we are not currently on OD, we must account for the overhead to start it.
        is_on_od = (last_cluster_type == ClusterType.ON_DEMAND)
        od_threshold = safety_margin if is_on_od else (overhead + safety_margin)
        
        # Critical Path: If slack is exhausted, use OD immediately
        if slack < od_threshold:
            return ClusterType.ON_DEMAND
            
        # Cost Optimization: Use Spot if available and safe
        if has_spot:
            if is_on_od:
                # If we are currently on OD, switching to Spot incurs an overhead cost.
                # We should only switch if we have enough slack to pay that cost AND 
                # switch back to OD (with another overhead) if Spot fails immediately.
                # This prevents a "death spiral" where switching consumes the safety buffer.
                switch_threshold = 2.0 * overhead + safety_margin
                
                if slack > switch_threshold:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # If coming from NONE or SPOT, and Spot is available, use it.
                return ClusterType.SPOT
        
        # If Spot is unavailable but we have plenty of slack, pause (NONE) to save money.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
