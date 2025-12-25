from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_commit_od"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._commit_to_od = False
        self._extra_buffer_seconds = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_done_seconds(self) -> float:
        try:
            if not self.task_done_time:
                return 0.0
            done = float(sum(self.task_done_time))
            if done < 0:
                return 0.0
            return min(done, float(self.task_duration))
        except Exception:
            # Fallback in case task_done_time is not a list of floats
            return 0.0

    def _remaining_work_seconds(self) -> float:
        done = self._compute_done_seconds()
        remain = float(self.task_duration) - done
        if remain < 0.0:
            return 0.0
        return remain

    def _safety_buffer_seconds(self) -> float:
        # Commit buffer = restart overhead + 2 gaps + small constant buffer
        # This provides margin for discretization and overhead reset.
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Use a moderate constant buffer to avoid cutting too close
        const_buf = 300.0  # 5 minutes
        return overhead + 2.0 * gap + const_buf

    def _should_commit_to_od(self) -> bool:
        # Determine if we must switch to OD now to guarantee meeting deadline.
        t = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remain = self._remaining_work_seconds()
        slack = deadline - t - remain
        safety = self._safety_buffer_seconds()
        return slack <= safety

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to OD, continue using OD until completion.
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Check if work is already complete; if so, do nothing.
        if self._remaining_work_seconds() <= 0.0:
            return ClusterType.NONE

        # Decide whether to commit to OD based on remaining slack.
        if self._should_commit_to_od():
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prioritize SPOT when available; if not, wait (NONE).
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)