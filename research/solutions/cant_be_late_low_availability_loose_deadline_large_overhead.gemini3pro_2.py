from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "SlackAwareScheduling"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If effectively done, stop
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        # Time management
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time

        # Calculate overhead required if we switch to On-Demand (OD) now.
        # If already on OD, overhead is 0. If not, we pay restart overhead.
        od_switch_overhead = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            od_switch_overhead = self.restart_overhead

        # Calculate total time required to finish if we commit to OD immediately
        time_needed_on_od = work_remaining + od_switch_overhead

        # Determine safety buffer
        # We need to account for the discrete time step (gap_seconds).
        # If we wait one more step, we consume gap_seconds of time.
        # We use a multiplier (2.0) to ensure we switch before crossing the critical threshold.
        safety_buffer = 2.0 * self.env.gap_seconds

        # Calculate slack (excess time available)
        slack = time_remaining - time_needed_on_od

        # Decision Logic:
        # 1. Safety First: If slack is dangerously low, use On-Demand to guarantee completion.
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND

        # 2. Cost Optimization: If we have slack, prefer Spot instances.
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Wait: If Spot is unavailable but we have slack, pause (NONE) to save money.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)