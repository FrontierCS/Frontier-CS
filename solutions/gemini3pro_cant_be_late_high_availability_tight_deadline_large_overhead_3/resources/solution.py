from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_slack_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate current progress and constraints
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done
        
        # If task is complete, do nothing
        if work_rem <= 0:
            return ClusterType.NONE

        time_rem = self.deadline - elapsed
        slack = time_rem - work_rem
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        # Buffer to account for discrete time steps and float precision
        buffer = 2.0 * gap + 1.0

        # 1. Survival Check
        # Determine minimum slack required to guarantee completion via On-Demand.
        # If we are not currently ON_DEMAND, we incur overhead to switch/start.
        switch_cost = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead
        min_survival_slack = switch_cost + buffer
        
        if slack < min_survival_slack:
            # Not enough slack to risk anything else; must use guaranteed resource
            return ClusterType.ON_DEMAND

        # 2. Economic Optimization
        # If we have excess slack, we prioritize Spot instances to minimize cost.
        # We need enough slack to cover:
        # a) The overhead to enter Spot (if not already there)
        # b) The overhead to switch back to On-Demand later if Spot fails
        
        threshold_new_spot = 2.0 * overhead + buffer
        
        if slack > threshold_new_spot:
            # We have sufficient slack to attempt Spot usage
            if has_spot:
                return ClusterType.SPOT
            else:
                # Spot unavailable, but we have enough slack to wait and save money
                return ClusterType.NONE
        else:
            # Slack is limited (between survival limit and comfortable spot entry)
            # Strategy: Maintain status quo if on Spot, otherwise fall back to OD
            if last_cluster_type == ClusterType.SPOT and has_spot:
                # We are already on Spot, entry cost is sunk. 
                # Survival check passed, so we have enough buffer for a future switch.
                return ClusterType.SPOT
            else:
                # Cannot afford the risk of entering Spot or waiting
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
