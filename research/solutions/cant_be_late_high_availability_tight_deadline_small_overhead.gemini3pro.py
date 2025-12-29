from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate the remaining work.
        # self.task_done_time contains a list of durations of fully completed segments.
        # While a job is running, the current segment is not yet in this list, 
        # causing work_remaining to appear larger than it technically is.
        # This results in conservative behavior (staying in OD/Panic mode longer), which is safe.
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the task is effectively complete, do nothing.
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        # Priority 1: Use Spot instances whenever available.
        # Spot instances are significantly cheaper (~1/3rd price). Even with a 3-minute 
        # restart overhead, the cost savings for a long task (48h) justify switching 
        # to Spot immediately when available.
        if has_spot:
            return ClusterType.SPOT

        # Priority 2: Ensure Deadline Satisfaction.
        # If Spot is not available, we must decide whether to wait (NONE) or use On-Demand (OD).
        # We want to wait as long as possible to maximize the chance of Spot becoming available.
        # However, we must start OD before it becomes impossible to finish by the deadline.
        
        elapsed = self.env.elapsed_seconds
        time_until_deadline = self.deadline - elapsed
        
        # Define a safety buffer to handle simulation step gaps and minor timing fluctuations.
        # 30 minutes (1800s) is chosen as a safe margin given the 4-hour slack.
        safety_buffer = 1800
        
        # Calculate the minimum time required to finish the job from a stopped state.
        # We include the restart_overhead because starting OD will incur this penalty.
        time_required_to_finish = work_remaining + self.restart_overhead
        
        # Check if we have reached the "Panic Threshold".
        # If the time remaining is less than what we need + buffer, we must use OD.
        if time_until_deadline <= (time_required_to_finish + safety_buffer):
            return ClusterType.ON_DEMAND

        # Priority 3: Wait and Save Cost.
        # If we have sufficient slack, we pause and wait for Spot instances to return.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)