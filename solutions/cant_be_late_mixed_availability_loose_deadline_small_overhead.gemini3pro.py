from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        # If work is effectively done, stop (safety check)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Time parameters
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        # Calculate time overhead to switch/start On-Demand.
        # If we are not currently running OD, we assume we must pay the overhead 
        # to switch to it in a worst-case scenario.
        if last_cluster_type == ClusterType.ON_DEMAND:
            transition_overhead = 0.0
        else:
            transition_overhead = self.restart_overhead
            
        # Slack is the time buffer available beyond the strict minimum needed to finish via On-Demand.
        # We subtract the potential transition overhead to be conservative.
        slack = remaining_time - (remaining_work + transition_overhead)
        
        # Safety Buffers (in seconds)
        # MIN_BUFFER: If slack drops below this, we panic and switch to On-Demand.
        # set to 30 minutes + 1 step gap to handle simulation granularity and safety.
        MIN_BUFFER = 1800.0 + self.env.gap_seconds
        
        # HYSTERESIS: If we are on On-Demand, we only switch back to Spot if slack is large.
        # This prevents thrashing (rapid switching) which incurs overhead cost and time loss.
        # Set to 1 hour.
        HYSTERESIS = 3600.0

        # 1. Critical Deadline Protection (Panic Mode)
        if slack < MIN_BUFFER:
            return ClusterType.ON_DEMAND

        # 2. Spot Instance Utilization
        if has_spot:
            # If currently on OD, check hysteresis before switching back to Spot
            if last_cluster_type == ClusterType.ON_DEMAND:
                if slack > HYSTERESIS:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            # If not on OD, use Spot immediately
            return ClusterType.SPOT

        # 3. Cost Saving Wait
        # If Spot is unavailable but we have plenty of slack, wait (NONE).
        # This consumes slack (time) but saves money compared to OD.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
