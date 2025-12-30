from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_static_commit"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize internal state; environment will be attached later.
        self._initialized = False
        self._force_on_demand = False
        self._commit_time = 0.0
        return self

    def _initialize_policy(self):
        # Compute when to permanently switch to on-demand to guarantee finishing.
        self._initialized = True
        self._force_on_demand = False

        # Default commit time is 0 (always on-demand) if anything goes wrong.
        commit_time = 0.0

        try:
            deadline = float(self.deadline)
            task_duration = float(self.task_duration)
            restart_overhead = float(self.restart_overhead)
            gap = float(getattr(self.env, "gap_seconds", 0.0))
        except Exception:
            self._commit_time = commit_time
            return

        # Total slack between task duration and hard deadline.
        slack = deadline - task_duration

        if slack <= 0:
            # No slack: safest is to run on-demand from the start.
            self._commit_time = 0.0
            return

        # Guard margin to account for discretization and at most one restart overhead
        # when switching to on-demand.
        # Use at least one gap or one restart_overhead, whichever is larger.
        guard_margin = max(gap, restart_overhead, 0.0)

        total_buffer = restart_overhead + guard_margin

        if total_buffer >= slack:
            # Not enough slack to safely play with spot: always on-demand.
            commit_time = 0.0
        else:
            # Run primarily on spot for (slack - total_buffer), then force on-demand.
            commit_time = slack - total_buffer
            if commit_time < 0.0:
                commit_time = 0.0

        self._commit_time = commit_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not getattr(self, "_initialized", False):
            self._initialize_policy()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))

        if not self._force_on_demand and elapsed >= self._commit_time:
            self._force_on_demand = True

        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)