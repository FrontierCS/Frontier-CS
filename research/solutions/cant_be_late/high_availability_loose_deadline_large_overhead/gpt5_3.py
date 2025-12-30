from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "never_late_v1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._committed_od = False
        self._commit_time = None
        self._last_reset_t = -1.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_if_new_run(self):
        # Detect new run by elapsed time reset
        try:
            elapsed = getattr(self.env, "elapsed_seconds", None)
            if elapsed is None:
                return
            if elapsed < 1e-9 or elapsed < self._last_reset_t:
                self._committed_od = False
                self._commit_time = None
                self._last_reset_t = elapsed
        except Exception:
            pass

    def _remaining_work(self):
        try:
            done = sum(self.task_done_time) if hasattr(self, "task_done_time") and self.task_done_time else 0.0
            return max(0.0, getattr(self, "task_duration", 0.0) - done)
        except Exception:
            return getattr(self, "task_duration", 0.0)

    def _time_left(self):
        try:
            return max(0.0, getattr(self, "deadline", 0.0) - getattr(self.env, "elapsed_seconds", 0.0))
        except Exception:
            return 0.0

    def _should_commit_now(self):
        # Commit to on-demand if the time left is just enough (or less) to finish with OD including one restart overhead
        remaining = self._remaining_work()
        left = self._time_left()

        if remaining <= 0.0:
            return False

        # If already on OD, overhead to continue is zero. Otherwise, pay restart overhead when switching.
        current = getattr(self.env, "cluster_type", None)
        overhead_if_switch = 0.0 if current == ClusterType.ON_DEMAND else getattr(self, "restart_overhead", 0.0)

        # Safety buffer to account for step granularity and rounding effects
        gap = max(0.0, getattr(self.env, "gap_seconds", 0.0))
        restart_overhead = getattr(self, "restart_overhead", 0.0)
        buffer = min(restart_overhead, max(gap, 0.0))

        need_time = remaining + overhead_if_switch + buffer
        return left <= need_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Reset per run state if new run detected
        self._reset_if_new_run()

        # If we're already done, do nothing
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        # Decide whether to commit to OD
        if not self._committed_od and self._should_commit_now():
            self._committed_od = True
            self._commit_time = getattr(self.env, "elapsed_seconds", None)

        # If committed, always use OD to guarantee completion
        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot when available; else wait (NONE)
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)