from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostAwareDeadlineStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        # Calculate total work done (sum of segments)
        work_done = sum(self.task_done_time)
        # Remaining work to be done
        work_rem = max(0.0, self.task_duration - work_done)
        # Remaining time until deadline
        time_rem = self.deadline - elapsed
        
        # If work is completed, stop using resources
        if work_rem <= 0:
            return ClusterType.NONE

        # Parameters for decision boundaries
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Safety Buffer Calculation:
        # We need to guarantee completion on On-Demand (OD).
        # Worst case: we are currently stopped or on Spot, so we must pay overhead to start OD.
        # Time needed = work_rem + overhead
        # We add buffers for:
        # 1. Simulation step size (gap): we might make decision slightly late
        # 2. Extra safety margin: to prevent failing due to tight tolerances
        # Using 1.5x overhead as fixed buffer + 2 steps of gap
        safety_buffer = (overhead * 1.5) + (gap * 2.0)
        
        # The critical time threshold. If remaining time drops below this, we risk missing the deadline.
        panic_threshold = work_rem + overhead + safety_buffer
        
        # 1. Panic Rule: Time is too tight, must use reliable OD
        if time_rem < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Hysteresis Rule: If we are already on OD and are reasonably close to the panic threshold,
        # stay on OD. This prevents oscillating (Spot <-> OD) which incurs multiple overhead penalties.
        # We define a band above the panic threshold where we "stick" to OD.
        hysteresis_band = overhead * 2.0
        if last_cluster_type == ClusterType.ON_DEMAND:
            if time_rem < panic_threshold + hysteresis_band:
                return ClusterType.ON_DEMAND

        # 3. Opportunity Rule: If Spot is available and we have slack, use it (Cheapest option)
        if has_spot:
            return ClusterType.SPOT
            
        # 4. Wait Rule: No Spot, but plenty of slack. Wait for Spot to return to save money.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
