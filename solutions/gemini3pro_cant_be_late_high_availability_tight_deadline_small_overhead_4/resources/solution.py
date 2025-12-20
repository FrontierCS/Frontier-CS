from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate current progress
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If work is already complete, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE

        # Current time state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        time_remaining = self.deadline - elapsed

        # Calculate "Safety Slack": the buffer we have before we MUST run On-Demand to finish.
        # If we are not currently on OD, we incur restart overhead to switch/start.
        cost_to_start_od = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            cost_to_start_od = self.restart_overhead
            
        required_time_on_od = work_remaining + cost_to_start_od
        slack = time_remaining - required_time_on_od
        
        # Define safety buffer. We need at least one 'gap' to make the decision in time.
        # Using 2.0 * gap provides a conservative margin against quantization/jitter.
        min_buffer = gap * 2.0
        
        # 1. Critical Condition: If slack is running out, we must use On-Demand.
        if slack < min_buffer:
            return ClusterType.ON_DEMAND
            
        # 2. Hysteresis: Avoid thrashing (switching OD <-> Spot repeatedly).
        # If we are already on OD, we stick with it unless we have accumulated significant slack.
        # Switching to OD increases the calculated slack (by removing cost_to_start_od).
        # We must ensure we have enough buffer to justify the risk of switching back to Spot.
        if last_cluster_type == ClusterType.ON_DEMAND:
            leave_od_threshold = min_buffer + (self.restart_overhead * 2.0)
            if slack < leave_od_threshold:
                return ClusterType.ON_DEMAND

        # 3. Cost Optimization: Use Spot if available and safe.
        if has_spot:
            return ClusterType.SPOT
            
        # 4. Wait Strategy: If Spot is unavailable but we have slack, wait (NONE) to save money.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
