from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_buffer_wait_spot"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_od = False
        self._progress_cache_sum = 0.0
        self._progress_cache_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Cache progress sum to avoid repeated O(n) summations
        if self.task_done_time is not None:
            cur_len = len(self.task_done_time)
            if cur_len != self._progress_cache_len:
                self._progress_cache_sum = sum(self.task_done_time)
                self._progress_cache_len = cur_len
            progress = self._progress_cache_sum
        else:
            progress = 0.0

        remaining = max(0.0, self.task_duration - progress)
        if remaining <= 1e-9:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        overhead = self.restart_overhead or 0.0

        # Safety buffer to ensure we can switch to OD and still finish on time
        safe_buffer = overhead + 3.0 * gap + 1e-6

        if time_left <= remaining + safe_buffer:
            self._commit_od = True

        if self._commit_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)