from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbl_robust_commit"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        try:
            done = sum(self.task_done_time) if self.task_done_time else 0.0
        except Exception:
            done = 0.0
        remaining = self.task_duration - done
        if remaining < 0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep using it to avoid overheads and guarantee finish
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(self.deadline)
        remaining_work = self._remaining_work()

        # If task already done (safety), do nothing
        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_time = deadline - now
        # Safety: if out of time, urgently use OD
        if remaining_time <= 0.0:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Compose a conservative margin:
        # - restart_overhead buffer for a single switch
        # - 2 step gaps to handle discretization and decision latency
        # - extra 10 minutes safety window
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        conservative_margin = restart_overhead + 2.0 * gap + 600.0  # seconds

        slack = remaining_time - remaining_work  # time we can waste before needing OD nonstop

        # If slack is at or below the conservative margin, commit to OD to guarantee finish
        if slack <= conservative_margin:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Opportunistic phase: use SPOT when available, otherwise wait
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
