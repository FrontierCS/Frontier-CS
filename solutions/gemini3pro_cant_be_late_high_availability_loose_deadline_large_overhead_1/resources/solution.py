from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "AdaptiveThresholdStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate panic threshold
        # We need enough time to finish on On-Demand (OD) if Spot becomes unavailable.
        # Minimum time = remaining_work + overhead (to start OD)
        # Safety buffer = 2 * overhead (resilience against spot fail + OD start) + 2 * gap + 15 mins padding
        safety_buffer = 2 * overhead + 2 * gap + 900
        panic_threshold = remaining_work + overhead + safety_buffer
        
        # 1. Panic Mode: If time is tight, force On-Demand
        if time_left < panic_threshold:
            return ClusterType.ON_DEMAND

        # 2. Opportunistic Spot Usage
        if has_spot:
            # Hysteresis: If currently on OD, only switch to Spot if we have significant slack
            # This prevents flapping and paying overheads when close to the critical path
            if last_cluster_type == ClusterType.ON_DEMAND:
                switch_buffer = 2 * overhead
                if time_left > panic_threshold + switch_buffer:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            return ClusterType.SPOT

        # 3. Cost Saving: Wait if Spot is unavailable and we have slack
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
