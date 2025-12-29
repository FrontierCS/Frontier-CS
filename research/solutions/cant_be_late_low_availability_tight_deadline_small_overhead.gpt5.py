from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_robust_commit_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self._committed_to_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_fudge(self) -> float:
        # Conservative safety buffer accounting for decision discretization and restart overhead.
        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        r = getattr(self, "restart_overhead", 180.0) or 180.0
        # 2 gaps + one restart overhead, capped to not exceed 25% of slack
        deadline = getattr(self, "deadline", 0.0) or 0.0
        task_duration = getattr(self, "task_duration", 0.0) or 0.0
        slack = max(0.0, deadline - task_duration)
        fudge = min(2.0 * gap + r, max(0.0, 0.25 * slack))
        # Ensure at least one gap worth of buffer
        return max(gap, fudge)

    def _remaining_work(self) -> float:
        done = 0.0
        td = getattr(self, "task_done_time", 0.0)
        if isinstance(td, (list, tuple)):
            done = float(sum(td))
        else:
            try:
                done = float(td)
            except Exception:
                done = 0.0
        total = getattr(self, "task_duration", 0.0) or 0.0
        rem = max(0.0, total - done)
        return rem

    def _must_start_on_demand_now(self) -> bool:
        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        time_left = max(0.0, deadline - elapsed)

        rem_work = self._remaining_work()
        # If we're already on OD, no extra restart overhead is needed to continue.
        if getattr(self.env, "cluster_type", None) == ClusterType.ON_DEMAND:
            overhead_to_switch = 0.0
        else:
            overhead_to_switch = getattr(self, "restart_overhead", 0.0) or 0.0

        fudge = self._compute_fudge()
        return time_left <= rem_work + overhead_to_switch + fudge

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to OD, stay there to avoid extra overhead and risk.
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # If we must start OD now to guarantee deadline, do it and commit.
        if self._must_start_on_demand_now():
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, we can still rely on cheap compute or wait.
        if has_spot:
            return ClusterType.SPOT

        # Pause if no spot and we still have slack; this avoids early OD spend.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)