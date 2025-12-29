from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        total_work = self.task_duration
        done_work = sum(self.task_done_time)
        
        rem_work = total_work - done_work
        rem_time = deadline - elapsed
        
        # If work is completed
        if rem_work <= 1e-6:
            return ClusterType.NONE
            
        # Safety buffer to account for step granularity and float precision
        buffer = 2.0 * gap
        
        # Calculate the "Panic Threshold":
        # The latest time we must start On-Demand to guarantee finishing.
        # We assume worst-case: we need to incur restart overhead (delta) + work time.
        # If rem_time is below this, we must use On-Demand immediately.
        panic_threshold = rem_work + overhead + buffer
        
        if rem_time < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # If we are here, we have slack (rem_time >= panic_threshold)
        
        if last_cluster_type == ClusterType.ON_DEMAND:
            # We are currently on OD. To switch back to Spot (or wait), we need extra slack.
            # Switching incurs overhead. If we switch to Spot and it fails immediately,
            # we pay overhead to go back to OD.
            # We enforce a hysteresis buffer to prevent oscillation.
            hysteresis = overhead + buffer
            
            if rem_time > panic_threshold + hysteresis:
                if has_spot:
                    return ClusterType.SPOT
                else:
                    return ClusterType.NONE
            else:
                # Keep holding OD as we are relatively close to the threshold
                return ClusterType.ON_DEMAND
        else:
            # We are not on OD. We have slack.
            # Use Spot if available to minimize cost.
            # If not available, wait (NONE) to save money, since we are safe.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)