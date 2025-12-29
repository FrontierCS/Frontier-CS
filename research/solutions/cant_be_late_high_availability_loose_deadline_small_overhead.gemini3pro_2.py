from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostOptimizedStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy. Returns self as per API requirements.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the cluster type for the current time step based on deadline constraints
        and cost minimization.
        """
        # Calculate remaining work
        total_done = sum(self.task_done_time)
        work_remaining = self.task_duration - total_done

        # If work is complete, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate time remaining until deadline
        time_remaining = self.deadline - self.env.elapsed_seconds

        # Determine the "Panic Threshold":
        # If we wait too long, we won't be able to finish even with guaranteed On-Demand instances.
        # We must account for:
        # 1. The actual work remaining.
        # 2. The restart overhead (incurred if we switch to On-Demand or start from stopped).
        # 3. A safety buffer to handle the discrete time step granularity (gap_seconds).
        #
        # If we switch to OD, we might pay 'restart_overhead'.
        # We check the condition every 'gap_seconds'.
        # We need: time_remaining > work_remaining + restart_overhead
        # To be safe against stepping over the limit between checks, we add a buffer of ~2 gaps.
        
        safety_buffer = 2.5 * self.env.gap_seconds
        panic_threshold = work_remaining + self.restart_overhead + safety_buffer

        # Critical Condition: If slack is exhausted, force On-Demand to guarantee completion.
        if time_remaining < panic_threshold:
            return ClusterType.ON_DEMAND

        # Cost Optimization Strategy:
        # If we have sufficient slack (above panic threshold):
        # - Use Spot instances if available (cheapest option).
        # - If Spot is unavailable, return NONE (pause) to save money and wait for Spot,
        #   consuming slack rather than paying for expensive On-Demand.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)