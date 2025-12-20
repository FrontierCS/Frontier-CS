from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Calculate remaining work and time
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If work is effectively done, stop
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_until_deadline = self.deadline - current_time
        
        # 2. Calculate Slack
        # We calculate slack conservatively: "How much extra time do we have 
        # if we were forced to restart On-Demand right now?"
        # We include restart_overhead to prevent flapping (switching back and forth)
        # when close to the buffer threshold.
        time_required_conservative = work_remaining + self.restart_overhead
        slack = time_until_deadline - time_required_conservative
        
        # 3. Define Safety Buffer
        # Reserve a buffer to handle simulation time steps and overhead risks.
        # 1800 seconds (30 mins) is safe given the large total slack (22h).
        # We also ensure it covers at least 2 simulation steps.
        gap = self.env.gap_seconds if hasattr(self.env, 'gap_seconds') else 300
        safety_buffer = max(1800.0, gap * 2.0)

        # 4. Decision Logic
        
        # Case A: Panic Mode
        # If our slack is running out, we must prioritize completion over cost.
        # We switch to (or stay on) On-Demand to guarantee the deadline is met.
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND
            
        # Case B: Standard Mode
        # If we have sufficient slack, we prioritize cost.
        # If Spot instances are available, use them.
        if has_spot:
            return ClusterType.SPOT
            
        # Case C: Wait Mode
        # If Spot is unavailable but we have plenty of slack, we wait (NONE).
        # This avoids the high cost of On-Demand, effectively trading slack for potential savings.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
