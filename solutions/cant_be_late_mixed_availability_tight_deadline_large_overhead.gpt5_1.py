from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_safe_spot_then_od_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self.commit_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        try:
            done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        except Exception:
            done = 0.0
        remaining = float(self.task_duration) - done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _safe_margin(self) -> float:
        # Minimal buffer to avoid off-by-one due to discretization and overhead handling jitter
        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Keep a modest margin: one step plus a fraction of overhead
        return gap + 0.25 * overhead

    def _should_commit_to_od(self, now: float, remaining: float) -> bool:
        deadline = float(self.deadline)
        overhead = float(self.restart_overhead)
        latest_switch_time = deadline - overhead - remaining
        margin = self._safe_margin()
        return now >= (latest_switch_time - margin)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task already done, do nothing
        remaining = self._remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        # If already on OD, stay committed
        if self.env.cluster_type == ClusterType.ON_DEMAND:
            self.commit_od = True

        now = float(self.env.elapsed_seconds)
        # Decide if we must commit to on-demand to guarantee deadline
        if not self.commit_od and self._should_commit_to_od(now, remaining):
            self.commit_od = True

        if self.commit_od:
            return ClusterType.ON_DEMAND

        # Not committed: prefer spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: wait if safe, else switch to OD
        if not self._should_commit_to_od(now, remaining):
            return ClusterType.NONE

        self.commit_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
