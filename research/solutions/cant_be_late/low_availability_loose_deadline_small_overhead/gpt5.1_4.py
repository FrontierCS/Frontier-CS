from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_threshold_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization hook; spec_path can be used if needed.
        # Initialize strategy state here.
        self.force_on_demand = False
        self.commit_time = None
        self._safety_margin = None
        return self

    def _initialize_policy_params(self):
        # Ensure attributes exist with safe fallbacks.
        deadline = getattr(self, "deadline", None)
        task_duration = getattr(self, "task_duration", None)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        # If critical parameters are missing, fall back to safest behavior:
        # always run on-demand.
        if deadline is None or task_duration is None:
            self.commit_time = 0.0
            self._safety_margin = 0.0
            return

        gap = float(getattr(self.env, "gap_seconds", 0.0))

        # Safety margin to account for discretization and any model mismatch.
        # Use:
        #   - 2 * step size
        #   - at least one restart_overhead
        #   - at least 10 minutes
        extra_safety = max(2.0 * gap, restart_overhead, 600.0)

        # Worst-case planning: assume zero progress before commit_time.
        # We require that, starting at commit_time, we can run a full job
        # with one restart_overhead and still finish before the deadline.
        commit_time = float(deadline) - float(task_duration) - restart_overhead - extra_safety

        # If this is negative, we must commit to on-demand immediately.
        if commit_time < 0.0:
            commit_time = 0.0

        self.commit_time = commit_time
        self._safety_margin = extra_safety

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure state attributes exist even if solve() was not called.
        if not hasattr(self, "force_on_demand"):
            self.force_on_demand = False
        if not hasattr(self, "commit_time"):
            self.commit_time = None

        # Lazy initialization once environment/task parameters are available.
        if self.commit_time is None:
            self._initialize_policy_params()

        # Current elapsed time.
        current_time = float(getattr(self.env, "elapsed_seconds", 0.0))

        # Decide if we must irrevocably switch to on-demand to guarantee deadline.
        if (not self.force_on_demand) and (current_time >= float(self.commit_time)):
            self.force_on_demand = True

        # Once committed, always use on-demand to avoid any further risk.
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Before commit time: use spot when available, else pause to save cost.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)