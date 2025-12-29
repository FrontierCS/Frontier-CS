from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization: we don't use spec_path but set internal state.
        self._policy_initialized = False
        self._lock_on_demand = False
        return self

    def _initialize_policy(self):
        if getattr(self, "_policy_initialized", False):
            return

        env = self.env
        gap = getattr(env, "gap_seconds", 60.0) or 60.0
        r = getattr(self, "restart_overhead", 0.0) or 0.0

        # Safety thresholds (in seconds).
        # base_spot_slack: minimum slack needed to continue using spot safely.
        # We require room for two restart overheads plus a small margin for
        # discretization.
        margin_steps = 2.0  # extra safety margin in units of gap_seconds
        margin = margin_steps * gap
        self._base_spot_slack = 2.0 * r + margin

        # base_wait_slack: if slack is above this, we can afford to wait (NONE)
        # when spot is unavailable; below this, we should start on-demand if
        # spot is down.
        wait_extra_steps = 10.0
        self._base_wait_slack = self._base_spot_slack + wait_extra_steps * gap

        self._policy_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy initialization (in case solve() was not called).
        if not hasattr(self, "_lock_on_demand"):
            self._lock_on_demand = False
        if not hasattr(self, "_policy_initialized") or not self._policy_initialized:
            self._initialize_policy()

        env = self.env
        gap = env.gap_seconds

        # Estimate remaining work from number of completed segments.
        done_segments = len(self.task_done_time) if getattr(self, "task_done_time", None) is not None else 0
        progress = done_segments * gap
        remaining_work = max(self.task_duration - progress, 0.0)

        # If task is completed, do nothing.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - env.elapsed_seconds
        slack = time_left - remaining_work

        # If already locked into on-demand, keep using it.
        if self._lock_on_demand:
            return ClusterType.ON_DEMAND

        # If slack is non-positive, we're already behind: immediately switch to on-demand.
        if slack <= 0.0:
            self._lock_on_demand = True
            return ClusterType.ON_DEMAND

        # If slack is too small or we're extremely close to the deadline,
        # permanently switch to on-demand.
        if slack <= self._base_spot_slack or time_left <= self.restart_overhead + 2.0 * gap:
            self._lock_on_demand = True
            return ClusterType.ON_DEMAND

        # We have comfortable slack here.

        if has_spot:
            # Prefer spot when available and we're safe.
            return ClusterType.SPOT

        # No spot available.
        # If slack is still large, wait for spot to reappear.
        if slack > self._base_wait_slack:
            return ClusterType.NONE

        # Slack is shrinking: start on-demand now and stick with it.
        self._lock_on_demand = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)