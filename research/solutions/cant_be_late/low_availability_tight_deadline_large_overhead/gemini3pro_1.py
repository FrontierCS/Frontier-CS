from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_slack_strategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work needed
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If work is completed, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Calculate time remaining until deadline
        elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed
        
        # Calculate time needed to finish using the safest resource (On-Demand)
        # If we are not currently on OD, we must pay overhead to switch to it.
        # If we are on OD, we continue without overhead.
        overhead = self.restart_overhead
        if last_cluster_type == ClusterType.ON_DEMAND:
            time_needed_safe = remaining_work
        else:
            time_needed_safe = remaining_work + overhead
            
        # Slack is the time buffer we have before we MUST run OD to finish
        slack = time_remaining - time_needed_safe
        
        # Safety buffer to account for discrete time steps
        # We want to act before slack drops below zero.
        gap = self.env.gap_seconds
        safety_buffer = 1.5 * gap
        
        # Strategy Logic:
        
        # 1. Critical Condition: If slack is exhausted, use OD immediately.
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND
            
        # 2. If Spot is available, prioritize it to save cost.
        if has_spot:
            # If we are currently on OD, switching to Spot incurs overhead.
            # Only switch if we have excess slack to absorb the overhead and prevent thrashing.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # If we switch: slack decreases by overhead immediately.
                # We also lose 'gap' time during this step.
                # Ensure resulting slack is still safe.
                if slack > (overhead + safety_buffer + gap):
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # Currently on Spot or None -> Use Spot
                return ClusterType.SPOT
                
        # 3. If Spot is unavailable but we have slack, Wait (NONE).
        # This preserves budget for when Spot becomes available.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)