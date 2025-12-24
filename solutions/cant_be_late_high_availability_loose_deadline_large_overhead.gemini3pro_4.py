from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "Safe_Threshold_Strategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        total_duration = self.task_duration
        
        # Calculate remaining work
        if self.task_done_time:
            done = sum(self.task_done_time)
        else:
            done = 0.0
        remaining = total_duration - done

        # If task is complete, stop
        if remaining <= 0:
            return ClusterType.NONE

        time_left = deadline - elapsed

        # Thresholds
        # 1. Panic Threshold: The absolute latest we can switch to On-Demand (OD)
        #    We need enough time to pay the restart overhead (to boot OD) + time to do the work.
        #    Added 2*gap for safety against discrete time steps.
        threshold_panic = remaining + overhead + (2.0 * gap)

        # 2. Safe Spot Threshold: The minimum time needed to safely *start* a new Spot instance.
        #    If we start Spot, we pay 'overhead'. If it finishes booting and then fails,
        #    we must still be above 'threshold_panic' to safely switch to OD.
        #    So we need: time_left - overhead >= threshold_panic
        #    Implies: time_left >= remaining + 2*overhead + 2*gap
        threshold_safe_spot = remaining + (2.0 * overhead) + (2.0 * gap)

        # Logic
        
        # 1. If we are critically close to the deadline, force OD.
        #    This condition overrides everything to ensure we don't violate the deadline.
        if time_left <= threshold_panic:
            return ClusterType.ON_DEMAND

        # 2. If Spot is available, try to use it
        if has_spot:
            # If we are already on Spot, we continue until the panic threshold.
            # We don't pay overhead to continue, so we don't need the extra buffer.
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            
            # If we are NOT on Spot (NONE or OD), we are starting a new Spot instance.
            # We must check if we have enough buffer to pay the boot cost and still be safe.
            if time_left > threshold_safe_spot:
                return ClusterType.SPOT
            else:
                # We are in the "Yellow Zone": Safe for OD, but unsafe to start Spot.
                # Use OD to guarantee completion.
                return ClusterType.ON_DEMAND

        # 3. If Spot is unavailable
        #    We have slack (time_left > threshold_panic).
        #    Waiting (NONE) is free and safe until we hit the panic threshold.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
