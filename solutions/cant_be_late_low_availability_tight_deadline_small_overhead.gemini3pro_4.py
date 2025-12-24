from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate work done and remaining
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If task is complete, stop
        if work_remaining <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed
        
        # Calculate slack: extra time available beyond minimum work required
        slack = time_remaining - work_remaining
        
        # Parameters
        R = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Panic Threshold: Minimum slack required to guarantee completion via On-Demand.
        # We need 'R' time for the restart overhead when switching to OD.
        # We include '2.0 * gap' as a safety buffer for step granularity and latency.
        panic_threshold = R + 2.0 * gap
        
        # Logic:
        # 1. If we are currently using On-Demand (safe mode)
        if last_cluster_type == ClusterType.ON_DEMAND:
            if has_spot:
                # Consider switching to Spot to save money.
                # Switching costs 'R' (overhead). This reduces effective slack.
                # We require slack to remain comfortably above the panic threshold after the switch.
                # Added 'gap' for hysteresis to prevent rapid switching.
                if slack > panic_threshold + R + gap:
                    return ClusterType.SPOT
                else:
                    # Not enough slack to risk switching; stay safe.
                    return ClusterType.ON_DEMAND
            else:
                # Spot unavailable, must stay on OD.
                return ClusterType.ON_DEMAND
                
        # 2. If we are not using On-Demand (Spot or None)
        if has_spot:
            # Spot is available. Use it.
            # Even if slack is low, using Spot (if contiguous) avoids the immediate 'R' penalty of switching to OD.
            return ClusterType.SPOT
        else:
            # Spot is unavailable.
            if slack < panic_threshold:
                # We are running out of time. Must use On-Demand to guarantee deadline.
                return ClusterType.ON_DEMAND
            else:
                # We have enough slack to wait for Spot availability.
                # Waiting costs 0 money, but consumes slack.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
