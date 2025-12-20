import inspect
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_spot_first_fallback_v1"

    def __init__(self, args=None):
        # Robustly initialize the base Strategy class.
        try:
            sig = inspect.signature(Strategy.__init__)
            params = list(sig.parameters.values())
            if len(params) <= 1:
                Strategy.__init__(self)
            else:
                Strategy.__init__(self, args)
        except Exception:
            try:
                Strategy.__init__(self, args)
            except Exception:
                pass

        self.args = args
        self._commit_time = None
        self._forced_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _ensure_initialized(self):
        if self._commit_time is not None:
            return

        env = getattr(self, "env", None)

        gap = getattr(env, "gap_seconds", 0.0) if env is not None else 0.0
        try:
            gap = float(gap)
        except Exception:
            gap = 0.0

        task_duration = getattr(self, "task_duration", 0.0)
        try:
            task_duration = float(task_duration)
        except Exception:
            task_duration = 0.0

        restart_overhead = getattr(self, "restart_overhead", 0.0)
        try:
            restart_overhead = float(restart_overhead)
        except Exception:
            restart_overhead = 0.0

        deadline = getattr(self, "deadline", 0.0)
        try:
            deadline = float(deadline)
        except Exception:
            deadline = 0.0

        # Reserve enough time at the end to complete the entire task on on-demand
        # from scratch, including one restart overhead and one step of slack to
        # account for discretization.
        safety_buffer = gap
        reserve_time = task_duration + restart_overhead + safety_buffer
        if reserve_time < 0.0:
            reserve_time = 0.0

        commit_time = deadline - reserve_time
        if commit_time < 0.0:
            commit_time = 0.0

        self._commit_time = commit_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        env = getattr(self, "env", None)
        elapsed = getattr(env, "elapsed_seconds", 0.0) if env is not None else 0.0
        try:
            elapsed = float(elapsed)
        except Exception:
            elapsed = 0.0

        if (not self._forced_on_demand) and (elapsed >= self._commit_time):
            self._forced_on_demand = True

        if self._forced_on_demand:
            return ClusterType.ON_DEMAND

        # Before we commit to on-demand, use spot when available, otherwise pause.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
