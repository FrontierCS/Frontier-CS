from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_buffered_policy_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._commit_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_task_done(self) -> float:
        td = getattr(self, "task_done_time", 0.0)
        try:
            if td is None:
                return 0.0
            if isinstance(td, (int, float)):
                return float(td)
            return float(sum(td))
        except Exception:
            try:
                return float(sum(list(td)))
            except Exception:
                return 0.0

    def _compute_margin_seconds(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 0.0)
        restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Safety buffer: at least two steps to avoid discretization issues, and 15 minutes additional guard.
        fudge = max(2.0 * gap, 900.0)
        return restart + fudge

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        total_task = float(getattr(self, "task_duration", 0.0) or 0.0)

        done = self._sum_task_done()
        remaining = max(0.0, total_task - done)

        if remaining <= 1e-9:
            return ClusterType.NONE

        margin = self._compute_margin_seconds()
        slack = (deadline - elapsed) - remaining

        if not self._commit_to_od:
            commit_time = deadline - (remaining + margin)
            if elapsed >= commit_time - 1e-9:
                self._commit_to_od = True
            elif slack <= margin:
                self._commit_to_od = True

        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide to wait or switch to on-demand
        allowed_wait = slack - margin
        if allowed_wait > 0:
            return ClusterType.NONE

        self._commit_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        try:
            args, _ = parser.parse_known_args()
        except Exception:
            args = None
        return cls(args)
