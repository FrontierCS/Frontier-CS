from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostOptimalSlackStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        # task_done_time is a list of completed segments, sum gives total progress
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        
        # If task is effectively done, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Calculate Slack
        # Slack represents the time buffer we have before we MUST run On-Demand to finish.
        # We calculate the time needed to finish if we switch to OD immediately.
        # We include 'overhead' to be conservative (assuming we might need to spin up OD).
        time_left = deadline - elapsed
        time_needed_od = remaining_work + overhead
        slack = time_left - time_needed_od

        # Define Thresholds
        # panic_buffer: Minimum slack required to feel safe. 
        # Needs to cover the time step gap (since we can't react instantly) and 
        # a small margin for float precision or jitter.
        panic_buffer = 2.0 * gap + 0.1 * overhead
        
        # recovery_buffer: Slack required to switch back from OD to Spot.
        # If we switch to Spot, we incur overhead (time lost). 
        # We ensure that after paying this overhead, we still have enough slack (> panic_buffer).
        recovery_buffer = panic_buffer + 1.1 * overhead

        # 1. Panic Logic: Deadline approaching, must guarantee progress
        if slack < panic_buffer:
            return ClusterType.ON_DEMAND

        # 2. Hysteresis: Prevent thrashing if we are already on OD
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Only switch back to Spot if we have accumulated significant slack
            if slack < recovery_buffer:
                return ClusterType.ON_DEMAND

        # 3. Spot Availability Logic
        if has_spot:
            # Slack is healthy and Spot is available -> Minimize cost
            return ClusterType.SPOT
        else:
            # Slack is healthy but Spot unavailable -> Wait (NONE) to save money
            # (Burning slack is cheaper than burning money on OD, as long as slack > panic_buffer)
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)