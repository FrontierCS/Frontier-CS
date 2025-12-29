from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "LazyThresholdStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work (seconds)
        # self.task_done_time is a list of completed segments
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done
        
        # If task is finished, do nothing
        if work_rem <= 0:
            return ClusterType.NONE

        # Current time status
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        # Simulation parameters
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate Safety Threshold
        # We must ensure that we have enough time to finish the job using On-Demand instances
        # (which are reliable) even if we have to restart right now.
        # Required Time = Remaining Work + Restart Overhead
        # We add 'gap' because our decision commits us for the next 'gap' seconds.
        # If we choose NONE or SPOT now, we might lose 'gap' seconds of deadline slack.
        # We add a small margin (1.0s) for floating point stability.
        # Condition: If we wait/fail this step, will we still have (Work + Overhead) time left?
        safety_threshold = work_rem + overhead + gap + 1.0
        
        # 1. Panic Mode: If we are close to the deadline, force On-Demand.
        # This guarantees completion provided we haven't already passed the point of no return.
        if time_left <= safety_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Opportunity Mode: Use Spot if available (Cheapest active option)
        # We have enough slack to risk a Spot preemption or overhead.
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Wait Mode: Spot unavailable, but we have slack (Cheapest option: $0)
        # Wait for Spot to become available to save money.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)