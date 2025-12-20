from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_hysteresis"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Current state
        elapsed = self.env.elapsed_seconds
        # Calculate remaining work (total - done)
        remaining_work = self.task_duration - sum(self.task_done_time)
        deadline_time = self.deadline
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Time remaining until deadline
        time_remaining = deadline_time - elapsed

        # Calculate the slack available assuming we might need to perform a restart/switch 
        # to On-Demand later. The overhead is the cost of that potential future switch.
        # Formula: Slack = Time_Available - (Work_Needed + Switch_Overhead)
        spot_safety_slack = time_remaining - (remaining_work + overhead)
        
        # Safety buffer:
        # We need a margin to account for simulation discretization (gap) and small variances.
        # 5 minutes (300s) is robust against the 3-minute overhead + typical gaps.
        # We also ensure it's at least 2 steps wide.
        safety_buffer = max(300.0, 2.0 * gap)

        # Determine threshold for using On-Demand.
        # Hysteresis Logic:
        # 1. If we are currently on On-Demand, we require extra slack to switch back to Spot.
        #    This prevents "thrashing" where we switch to Spot, pay overhead, reduce slack, 
        #    and immediately have to switch back to OD.
        #    We need enough slack to absorb the switch overhead AND still be above the safety buffer.
        # 2. If we are not on On-Demand, we just check against the safety buffer.
        
        panic_threshold = safety_buffer
        if last_cluster_type == ClusterType.ON_DEMAND:
            panic_threshold += overhead

        # Strategy Logic
        
        # 1. Critical Check: Do we have enough time to risk not being on On-Demand?
        if spot_safety_slack < panic_threshold:
            return ClusterType.ON_DEMAND

        # 2. Economy Mode: If safe, use Spot if available.
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Wait Mode: Spot unavailable but we have plenty of slack.
        # Wait (NONE) to save money rather than burning budget on OD prematurely.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
