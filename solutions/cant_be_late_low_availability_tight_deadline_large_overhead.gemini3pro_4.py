from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def __init__(self, args):
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Parameters
        # MIN_SLACK: Buffer time (seconds) to handle step granularity and safety.
        # 900 seconds = 15 minutes.
        MIN_SLACK = 900.0
        
        # R: Restart overhead in seconds
        R = self.restart_overhead

        # 1. Current State Calculation
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_rem = max(0.0, self.task_duration - work_done)
        time_rem = self.deadline - elapsed

        # 2. Slack Calculation
        # Slack is the time buffer remaining if we were to finish the task using On-Demand.
        # If currently On-Demand, effective startup cost is 0.
        # If not (Spot or None), we need 'R' seconds to start On-Demand.
        start_cost_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else R
        time_needed_od = work_rem + start_cost_od
        slack = time_rem - time_needed_od

        # 3. Critical Safety Check
        # If slack drops below safe threshold, force On-Demand to ensure deadline is met.
        if slack < MIN_SLACK:
            return ClusterType.ON_DEMAND

        # 4. Resource Decision Logic (when Safe)
        if has_spot:
            # Spot is available. We prefer it for cost, but only if we can afford the transition risks.
            
            if last_cluster_type == ClusterType.SPOT:
                # We are already running Spot.
                # The slack calculation already assumed the cost R to switch to OD.
                # Since slack > MIN_SLACK, we are safe to continue.
                return ClusterType.SPOT
                
            elif last_cluster_type == ClusterType.ON_DEMAND:
                # Considering switch OD -> Spot.
                # Costs involved:
                # 1. Burn 'R' seconds of time starting Spot (reduces time_rem).
                # 2. Change state: 'start_cost_od' becomes R (was 0), reducing calculated slack by R.
                # Total impact on slack = 2 * R.
                if slack > MIN_SLACK + 2 * R:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            else: # last_cluster_type == ClusterType.NONE
                # Considering switch NONE -> Spot.
                # Costs involved:
                # 1. Burn 'R' seconds of time starting Spot.
                # 2. State change: start_cost_od is already R, so no formula change.
                # Total impact on slack = R.
                if slack > MIN_SLACK + R:
                    return ClusterType.SPOT
                else:
                    # Not enough slack to afford Spot startup.
                    # Since we are safe (slack > MIN_SLACK), we Wait (NONE) to save money/slack.
                    return ClusterType.NONE

        else:
            # Spot is NOT available.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # If we are already paying for OD, stay on it.
                # Switching off risks paying restart overhead later.
                return ClusterType.ON_DEMAND
            else:
                # If we are not running, and safe, wait for Spot to return.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
