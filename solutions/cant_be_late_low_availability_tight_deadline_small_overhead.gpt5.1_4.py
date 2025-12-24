from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self._safety_margin_seconds = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_if_needed(self):
        if self._safety_margin_seconds is not None:
            return

        env = getattr(self, "env", None)
        if env is None:
            self._safety_margin_seconds = 3600.0
            return

        try:
            gap = float(getattr(env, "gap_seconds", 60.0) or 60.0)
        except Exception:
            gap = 60.0

        try:
            deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        except Exception:
            deadline = 0.0

        try:
            duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        except Exception:
            duration = 0.0

        try:
            overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        except Exception:
            overhead = 0.0

        slack0 = max(deadline - duration, 0.0)
        min_margin = max(3.0 * overhead, 4.0 * gap, 1e-6)
        base_margin = max(min_margin, 0.5 * 3600.0)

        if slack0 > 0.0:
            max_margin = 0.9 * slack0
            margin = min(base_margin, max_margin)
            if margin < 4.0 * gap:
                margin = 4.0 * gap
        else:
            margin = base_margin

        self._safety_margin_seconds = margin

    def _compute_remaining_work(self) -> float:
        try:
            done_list = getattr(self, "task_done_time", None)
            if not done_list:
                work_done = 0.0
            else:
                work_done = float(sum(done_list))
        except Exception:
            work_done = 0.0

        try:
            duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        except Exception:
            duration = 0.0

        remaining = duration - work_done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        remaining = self._compute_remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        try:
            elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        except Exception:
            elapsed = 0.0

        try:
            deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        except Exception:
            deadline = 0.0

        TL = deadline - elapsed
        if TL <= 0.0:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        margin = self._safety_margin_seconds

        if TL <= remaining + margin:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
