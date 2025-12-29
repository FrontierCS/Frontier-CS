from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "OptimizedDeadlineStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        rem_work = self.task_duration - work_done
        
        # If task is effectively complete, stop
        if rem_work <= 1e-6:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        
        # Safety margin calculation
        # We add a buffer to account for simulation step granularity and restart overheads.
        # 900 seconds (15 mins) plus 2 step intervals provides a robust safety net
        # to ensure we don't miss the deadline due to discretization or switching delays.
        margin = max(900.0, 2.0 * self.env.gap_seconds)
        
        # Calculate the "point of no return" (threshold)
        # If we wait longer than this, we risk not finishing even with On-Demand.
        # We include restart_overhead because switching to On-Demand might incur a startup delay.
        threshold = rem_work + self.restart_overhead + margin
        
        # 1. Deadline Protection (Highest Priority)
        # If we are approaching the threshold, force On-Demand usage to guarantee completion.
        if time_left < threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Cost Minimization
        # If we have slack (time_left >= threshold):
        if has_spot:
            # Prefer Spot instances as they are cheaper
            return ClusterType.SPOT
        else:
            # If Spot is unavailable but we still have slack, choose NONE (wait).
            # Waiting is free, whereas running On-Demand unnecessarily is expensive.
            # We only switch to On-Demand when the deadline constraint (above) forces us to.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)