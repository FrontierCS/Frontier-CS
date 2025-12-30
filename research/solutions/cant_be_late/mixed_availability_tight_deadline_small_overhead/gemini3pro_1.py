from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import math

class Solution(Strategy):
    NAME = "SafeSlackStrategy"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work and time
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - work_done)
        time_remaining = self.deadline - elapsed

        # If finished, stop
        if work_remaining <= 0:
            return ClusterType.NONE

        restart_overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Safety buffer configuration
        # Use a buffer of 15 minutes or 2 time steps, whichever is larger.
        # This protects against granularity issues and rapid Spot fluctuations.
        safety_buffer = max(900.0, 2.0 * gap)

        # Calculate the panic threshold
        # If time_remaining falls below this, we are at risk of missing the deadline
        # if we rely on Spot (which incurs overhead on preemption).
        # We reserve 'restart_overhead' implicitly to cover the switch cost to OD.
        panic_threshold = work_remaining + restart_overhead + safety_buffer

        # CRITICAL CONDITION: If we are close to the deadline, force ON_DEMAND.
        # This prioritizes avoiding the -100,000 penalty over cost savings.
        if time_remaining < panic_threshold:
            return ClusterType.ON_DEMAND

        # NORMAL OPERATION: Prefer Spot if available
        if has_spot:
            # If we were previously on ON_DEMAND, only switch back to SPOT if we have
            # substantial slack. This prevents "thrashing" where we switch back and forth
            # incurring overheads that negate the savings.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Require an extra buffer (hysteresis) to switch back to Spot
                if time_remaining > panic_threshold + safety_buffer:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            return ClusterType.SPOT

        # If Spot is unavailable and we are not in panic mode, wait (save money).
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)