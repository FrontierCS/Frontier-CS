from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostOptimizedSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate total work done so far (handle list or scalar)
        if isinstance(self.task_done_time, (list, tuple)):
            work_done = sum(self.task_done_time)
        else:
            work_done = self.task_done_time

        work_remaining = self.task_duration - work_done
        
        # If work is completed, stop
        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        deadline = self.deadline
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        time_remaining = deadline - current_time
        
        # Calculate time needed to finish if we start a new instance now.
        # This includes the work remaining, the restart overhead, and a safety buffer
        # to account for time step quantization (gap).
        # We use a safety buffer of 2 steps to ensure we don't miss the deadline due to discrete steps.
        safety_buffer = 2.0 * gap
        time_needed_if_start = work_remaining + overhead + safety_buffer
        
        # Slack is the time we can afford to wait/waste
        slack = time_remaining - time_needed_if_start
        
        if has_spot:
            # Spot is available
            
            # If we are currently running On-Demand, we should be careful about switching back to Spot.
            # Switching incurs overhead and reliability risk.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Heuristics for switching back to Spot:
                # 1. We must have significant slack (e.g., > 4x overhead) to absorb the restart cost and risk.
                # 2. We must have enough work remaining (e.g., > 10x overhead) to make the price difference pay off.
                
                safe_slack = slack > (4.0 * overhead)
                substantial_work = work_remaining > (10.0 * overhead)
                
                if safe_slack and substantial_work:
                    return ClusterType.SPOT
                else:
                    # Keep using On-Demand to avoid overhead/risk
                    return ClusterType.ON_DEMAND
            else:
                # If we were paused or using Spot, use Spot
                return ClusterType.SPOT
        
        else:
            # Spot is NOT available
            
            # If our slack is depleted (or negative), we are in the "danger zone".
            # We must use On-Demand to guarantee completion before the deadline.
            if slack <= 0:
                return ClusterType.ON_DEMAND
            else:
                # We have enough slack to wait for Spot to return.
                # Pausing (NONE) costs $0, whereas OD is expensive.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
