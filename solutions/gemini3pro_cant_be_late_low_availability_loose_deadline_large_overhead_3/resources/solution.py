from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the cluster type for the next time step.
        Prioritizes Spot instances to minimize cost, but switches to On-Demand
        when the deadline approaches to ensure completion (Least Laxity First).
        """
        # Calculate remaining work
        # self.task_done_time is a list of completed segment durations in seconds
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If work is effectively done, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        
        # Calculate safety buffer
        # We switch to On-Demand when:
        # time_left < remaining_work + restart_overhead + buffer
        #
        # restart_overhead: Time spent booting up the OD instance.
        # buffer: A safety margin to prevent deadline misses due to time step granularity
        #         or minor simulation variances.
        #         We use 30 minutes (1800s) + 3x the step size as a robust margin.
        #         The penalty for missing the deadline is severe (-100,000), so we
        #         are conservative with the deadline constraint.
        safety_buffer = 1800 + (3 * self.env.gap_seconds)
        
        panic_threshold = remaining_work + self.restart_overhead + safety_buffer
        
        # If we are in the "panic zone", we must use On-Demand to guarantee completion.
        if time_left < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # If we have slack, prefer Spot instances if available to save cost.
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable but we still have slack, wait (NONE) to save money.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
