from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Retrieve current state from the environment
        elapsed = self.env.elapsed_seconds
        # self.task_done_time is a list of completed segment durations
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If the task is effectively complete, stop
        if remaining_work <= 0:
            return ClusterType.NONE
            
        time_remaining = self.deadline - elapsed
        
        # Calculate the critical threshold time required to finish on On-Demand.
        # We assume the worst-case scenario where we must switch instance types immediately,
        # incurring the restart_overhead.
        # We add a safety buffer of 2 time steps (gap_seconds) to account for discrete time steps
        # and ensure we switch before it's mathematically impossible to finish.
        safety_buffer = 2.0 * self.env.gap_seconds
        required_time_on_od = remaining_work + self.restart_overhead + safety_buffer
        
        # Critical Condition: If time remaining is tight, force On-Demand usage.
        # This guarantees meeting the deadline (assuming On-Demand availability).
        if time_remaining <= required_time_on_od:
            return ClusterType.ON_DEMAND
            
        # Optimization Strategy (Slack available):
        # 1. Prefer Spot instances as they are significantly cheaper.
        if has_spot:
            return ClusterType.SPOT
            
        # 2. If Spot is unavailable but we still have slack (time_remaining > required_time_on_od),
        #    choose NONE (pause). This incurs 0 cost while waiting for Spot availability,
        #    utilizing the slack time to minimize total cost.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)