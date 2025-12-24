from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self._force_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand, keep using it.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        task_duration = self.task_duration
        restart_overhead = getattr(self, "restart_overhead", 0.0)

        time_left = deadline - elapsed

        # Conservative policy: assume zero progress towards task_duration.
        # Reserve enough time to run the entire task on on-demand, plus restart
        # overhead and a safety buffer to account for discretization and small errors.
        safety_buffer = max(5.0 * gap, 30.0 * 60.0)  # at least 30 minutes or 5 steps
        required_time_for_safe_fallback = task_duration + restart_overhead + safety_buffer

        slack = time_left - required_time_for_safe_fallback

        if slack <= 0:
            # No more room to wait; commit to on-demand for the rest of the job.
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Still in the slack region: we can try to exploit spot when available.
        if has_spot:
            return ClusterType.SPOT

        # No spot available; decide between idling and temporarily using on-demand.
        wait_threshold = max(2.0 * gap, 10.0 * 60.0)  # at least 10 minutes or 2 steps
        if slack > wait_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
