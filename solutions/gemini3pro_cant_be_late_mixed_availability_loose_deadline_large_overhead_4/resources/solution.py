from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work required
        # task_done_time is a list of completed segment durations
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        # If work is effectively done, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Calculate time strictly needed to finish if we rely on On-Demand from this point.
        # If we are not currently on On-Demand, we incur the restart overhead.
        switch_overhead = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_overhead = self.restart_overhead
            
        time_needed_on_demand = remaining_work + switch_overhead
        
        # Define a safety buffer.
        # We include self.restart_overhead in the buffer to create hysteresis.
        # This prevents "flapping" (switching back to Spot) if we are in the middle 
        # of On-Demand initialization and technically have a tiny bit of slack calculated 
        # without the overhead we've already committed to paying.
        # We also add a margin for discrete time steps and float precision.
        gap = self.env.gap_seconds if self.env.gap_seconds else 60.0
        buffer = self.restart_overhead + max(2.0 * gap, 600.0)
        
        # Calculate the latest wall-clock time we can start/continue On-Demand
        latest_safe_time = self.deadline - time_needed_on_demand - buffer
        
        # 1. Panic Condition: If we are close to the deadline, force On-Demand.
        # This ensures we satisfy the hard deadline constraint.
        if self.env.elapsed_seconds >= latest_safe_time:
            return ClusterType.ON_DEMAND
            
        # 2. Slack Availability: We have enough time buffer.
        # Prioritize Spot instances to minimize cost.
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Spot Unavailable but Slack Exists:
        # Wait (NONE) rather than burning money on On-Demand prematurely.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
