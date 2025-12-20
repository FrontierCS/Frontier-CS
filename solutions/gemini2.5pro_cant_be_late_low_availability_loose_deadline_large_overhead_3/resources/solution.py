import sys
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # Mean Time Between Preemptions (MTBP) in seconds.
        # This is the primary tuning parameter for the strategy's risk model,
        # representing our assumption about the spot environment's stability.
        # A lower MTBP leads to a more conservative strategy (larger safety buffer).
        # Given "Low availability (4-40%)" regions, a conservative estimate is prudent.
        # We assume an average of one preemption every 2 hours.
        self.MTBP = 2.0 * 3600.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # 1. Calculate current work progress.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the task is completed, do nothing.
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Determine time-to-deadline and slack.
        # The Point of No Return (PNR) is the latest moment to start on On-Demand
        # and still finish by the deadline.
        point_of_no_return = self.deadline - work_remaining
        
        # If past the PNR, we must use On-Demand.
        if self.env.elapsed_seconds >= point_of_no_return:
            return ClusterType.ON_DEMAND

        # Slack is the total time we can afford to be idle before missing the deadline.
        slack = self.deadline - self.env.elapsed_seconds - work_remaining

        # 3. Define risk zones based on slack and apply corresponding logic.

        # HIGH-RISK ZONE: If slack is less than a single restart overhead,
        # a single preemption could cause a deadline miss. We must use On-Demand.
        min_safety_buffer = self.restart_overhead
        if slack <= min_safety_buffer:
            return ClusterType.ON_DEMAND

        # CAUTION-ZONE: A larger, dynamic buffer accounts for future risk.
        # It grows with work remaining, as more work implies more potential preemptions.
        dynamic_safety_buffer = min_safety_buffer + self.restart_overhead * (work_remaining / self.MTBP)

        # If slack falls below this buffer, we are in the "caution zone".
        # We prefer Spot if available, but use On-Demand otherwise to preserve slack.
        if slack <= dynamic_safety_buffer:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        # SAFE-ZONE: If slack is plentiful, we can be aggressive in minimizing cost.
        # Use Spot when available and wait (cost-free) when it is not.
        else:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """Required for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)
