from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_threshold_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.args = args
        self._commit_slack = None
        self._use_on_demand_forever = False
        self._last_elapsed = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_threshold_if_needed(self):
        if self._commit_slack is None:
            overhead = float(getattr(self, "restart_overhead", 0.0))
            # Commit slack threshold in seconds: at least 1 hour, or 10× overhead
            self._commit_slack = max(3600.0, 10.0 * overhead)

    def _reset_if_new_episode(self):
        current_elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        if self._last_elapsed is None or current_elapsed < self._last_elapsed:
            self._commit_slack = None
            self._use_on_demand_forever = False
        self._last_elapsed = current_elapsed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_if_new_episode()
        self._initialize_threshold_if_needed()

        # Compute remaining work
        if self.task_done_time:
            work_done = float(sum(self.task_done_time))
        else:
            work_done = 0.0
        remaining_work = max(0.0, float(self.task_duration) - work_done)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        time_left = deadline - elapsed

        if time_left <= 0.0:
            # Already at/past deadline; best effort
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work

        if not self._use_on_demand_forever:
            if slack <= 0.0 or slack <= self._commit_slack:
                self._use_on_demand_forever = True

        if self._use_on_demand_forever:
            return ClusterType.ON_DEMAND

        # Pre-commit phase: prefer spot, wait when spot unavailable.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
