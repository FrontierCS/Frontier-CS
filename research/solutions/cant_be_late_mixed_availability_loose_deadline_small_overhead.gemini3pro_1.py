from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLate_CostOptimized"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Gather current state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        gap = self.env.gap_seconds

        # If task is completed (allow for small float epsilon)
        if work_remaining <= 1e-7:
            return ClusterType.NONE

        time_remaining = deadline - elapsed

        # Calculate the "Latest Start Time" logic for On-Demand (OD)
        # We must ensure we have enough time to finish using OD, which is reliable.
        # If we switch to OD from another type, we pay restart overhead.
        overhead_if_od = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_if_od = self.restart_overhead
            
        time_needed_od = work_remaining + overhead_if_od
        slack = time_remaining - time_needed_od

        # Safety buffer definition:
        # We must survive the current step (gap_seconds) without the slack dropping below zero.
        # If we choose NONE or if SPOT fails, slack decreases by 'gap'.
        # We use a multiplier (2.5x) to handle discrete time steps and provide a safety margin.
        safety_buffer = 2.5 * gap

        # Critical Condition: If slack is running out, force On-Demand
        if slack < safety_buffer:
            # "Desperate Mode" Optimization:
            # If switching to OD is impossible (slack < 0) because of the restart overhead,
            # but we are currently on a SPOT instance (overhead = 0 to continue) and it is available,
            # we stick with SPOT as the only path to potentially finish.
            if slack < 0:
                overhead_if_spot = 0.0 if last_cluster_type == ClusterType.SPOT else self.restart_overhead
                if has_spot and time_remaining > (work_remaining + overhead_if_spot):
                    return ClusterType.SPOT
            
            # Default safe action in critical zone
            return ClusterType.ON_DEMAND

        # Safe Condition: Optimize for cost
        if has_spot:
            return ClusterType.SPOT
        else:
            # If Spot is unavailable but we have plenty of slack, wait (NONE) to save money.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)