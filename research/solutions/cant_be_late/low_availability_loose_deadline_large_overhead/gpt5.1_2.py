from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_if_needed(self):
        if getattr(self, "_initialized_internal", False):
            return
        # All times are in seconds.
        # Conservative switching threshold to ensure we can always fall back
        # to on-demand and finish before the deadline, accounting for:
        # - Restart overhead once when switching off spot.
        # - Discrete time steps (gap_seconds) and potential rounding.
        slack = self.deadline - self.task_duration  # total slack versus pure OD
        # Subtract restart_overhead and 3 * gap_seconds as extra safety margin:
        #   - 1 * gap: for discretization before we decide to switch
        #   - 1 * gap: for possible overshoot on the final step
        #   - 1 * gap: additional safety buffer
        safe_slack = slack - self.restart_overhead - 3.0 * self.env.gap_seconds
        if safe_slack < 0.0:
            safe_slack = 0.0
        self._switch_time = safe_slack
        self._initialized_internal = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()
        t = self.env.elapsed_seconds

        # Before switch time: use spot if available, otherwise pause (NONE).
        if t < self._switch_time:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.NONE

        # After switch time: always on-demand to guarantee completion.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)