from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_strategy"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.args = args
        self._policy_initialized = False
        self._buffer_seconds = 0.0
        self._lock_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_policy(self):
        if self._policy_initialized:
            return
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        slack = max(0.0, deadline - task_duration)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)

        # Reserve some time buffer to absorb at least one restart and discretization.
        fraction = 0.05  # 5% of total slack if available
        buffer = max(
            2.0 * restart_overhead,  # at least one full restart + margin
            5.0 * gap,               # a few steps for discretization
            fraction * slack,        # fraction of slack for uncertainty
        )
        self._buffer_seconds = buffer
        self._policy_initialized = True

    def _compute_completed_work(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        total = 0.0
        first = segments[0]
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            for seg in segments:
                try:
                    start, end = seg[0], seg[1]
                    if end > start:
                        total += float(end - start)
                except Exception:
                    continue
        else:
            for v in segments:
                try:
                    total += float(v)
                except Exception:
                    continue
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        if elapsed == 0.0:
            # New episode: reset run-specific state.
            self._lock_to_od = False
            self._policy_initialized = False

        if not self._policy_initialized:
            self._initialize_policy()

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = self._compute_completed_work()
        remaining = max(0.0, task_duration - done)

        if remaining <= 0.0:
            return ClusterType.NONE

        deadline = float(getattr(self, "deadline", elapsed) or elapsed)
        time_left = deadline - elapsed

        if time_left <= 0.0:
            self._lock_to_od = True

        if not self._lock_to_od:
            if time_left <= remaining + self._buffer_seconds:
                self._lock_to_od = True

        if self._lock_to_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
