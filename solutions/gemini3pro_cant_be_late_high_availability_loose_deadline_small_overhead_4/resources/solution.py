from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostMinimizerStrategy"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy. Returns self as per API requirement.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the next cluster type based on remaining time, work, and spot availability.
        Implements a Least Slack First / Last Responsible Moment strategy.
        """
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If task is done, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE

        # Time state
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        # Constants
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate Panic Threshold
        # We must ensure we have enough time to finish using On-Demand (reliable).
        # Conservative estimate: Assume we might need to pay restart overhead.
        # Safety Buffer:
        # - 4.0 * overhead: robust margin for restart mechanics
        # - 10.0 * gap: robust margin for simulation step size granularity
        
        safety_buffer = (4.0 * overhead) + (10.0 * gap)
        required_time_on_od = work_remaining + overhead
        
        panic_threshold = required_time_on_od + safety_buffer
        
        # Logic:
        # 1. If time is critical, force On-Demand to guarantee deadline.
        if time_remaining < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. If time is not critical and Spot is available, use Spot (cheapest).
        if has_spot:
            return ClusterType.SPOT
            
        # 3. If Spot is unavailable but we have slack, wait (NONE) to save money.
        #    We will eventually hit the panic_threshold if Spot doesn't return.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
