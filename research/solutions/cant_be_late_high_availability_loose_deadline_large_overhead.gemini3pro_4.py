from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate total work completed so far
        # Assuming task_done_time is a list of duration floats
        completed_work = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = self.task_duration - completed_work

        # If work is effectively complete, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_until_deadline = self.deadline - current_time

        # Safety buffer calculation
        # We define a "panic threshold" to switch to On-Demand.
        # We must allow enough time for:
        # 1. The actual remaining work
        # 2. The restart overhead (in case we are not currently running or need to switch)
        # 3. A safety buffer to handle granular time steps and potential simulation jitter
        # Buffer chosen: 4x restart overhead + 5x time step gap
        safety_buffer = (4.0 * self.restart_overhead) + (5.0 * self.env.gap_seconds)
        
        required_time_for_od = remaining_work + self.restart_overhead + safety_buffer

        # Strategy Logic:

        # 1. Panic Mode: If we are close to the deadline, force On-Demand to guarantee completion.
        if time_until_deadline <= required_time_for_od:
            return ClusterType.ON_DEMAND

        # 2. Standard Mode: Prefer Spot instances to save cost.
        if has_spot:
            # Optimization: If we are already on On-Demand and the remaining work is very small 
            # (less than the time it takes to restart Spot), stay on On-Demand.
            # Switching would incur overhead that exceeds the remaining work time.
            if last_cluster_type == ClusterType.ON_DEMAND and remaining_work < self.restart_overhead:
                return ClusterType.ON_DEMAND
                
            return ClusterType.SPOT

        # 3. Wait Mode: Spot is unavailable, but we have plenty of slack.
        # Waiting costs 0, whereas running On-Demand is expensive.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)