from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work based on completed segments
        # sum(task_done_time) gives total seconds of work completed
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If task is complete, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_until_deadline = self.deadline - current_time
        
        # Determine the "safe time" required to finish using On-Demand instances.
        # If we are already on On-Demand, we can continue without restart overhead.
        # If we are on Spot or None, switching to On-Demand incurs the restart overhead.
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_to_switch = 0.0
        else:
            overhead_to_switch = self.restart_overhead

        time_needed_for_od = remaining_work + overhead_to_switch
        
        # Define a safety buffer to account for step granularity (gap_seconds).
        # We want to switch to OD slightly before the exact second required 
        # to ensure we don't miss the deadline due to discretization.
        gap = self.env.gap_seconds
        buffer = 2.0 * gap if gap else 60.0
        
        # CRITICAL DEADLINE CHECK:
        # If the remaining time is close to the bare minimum needed for OD, 
        # we must force On-Demand usage to guarantee completion.
        if time_until_deadline <= (time_needed_for_od + buffer):
            return ClusterType.ON_DEMAND

        # COST OPTIMIZATION STRATEGY (when Slack > Buffer):
        # 1. Use Spot instances if available (Cheapest option).
        # 2. If Spot is unavailable, return NONE (Wait).
        #    Waiting consumes slack but costs $0, whereas OD costs ~$3.06/hr.
        #    Since we have sufficient slack, we delay execution to save money.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)