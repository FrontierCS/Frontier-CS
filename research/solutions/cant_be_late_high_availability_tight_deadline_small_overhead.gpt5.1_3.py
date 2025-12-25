from typing import Any, List, Tuple, Union

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    # Safety margin before deadline (seconds)
    PADDING_SECONDS = 20 * 60  # 20 minutes

    def solve(self, spec_path: str) -> "Solution":
        # Optional: reset internal state
        self._initialized = False
        return self

    def _ensure_init(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._use_od_only: bool = False
        self._done_work_cache: float = 0.0
        self._last_done_len: int = 0
        self._segments_are_intervals: bool = False

    def _update_done_cache(self) -> None:
        """Incrementally compute total completed work seconds."""
        task_done_time: List[Any] = getattr(self, "task_done_time", []) or []
        n = len(task_done_time)
        if n == 0:
            self._done_work_cache = 0.0
            self._last_done_len = 0
            return

        # Detect representation on first non-empty update
        if self._last_done_len == 0:
            first = task_done_time[0]
            if isinstance(first, (tuple, list)) and len(first) >= 2:
                self._segments_are_intervals = True
            else:
                self._segments_are_intervals = False

        if n > self._last_done_len:
            new_segments = task_done_time[self._last_done_len : n]
            if self._segments_are_intervals:
                for seg in new_segments:
                    # Assume (start, end) in seconds
                    self._done_work_cache += float(seg[1] - seg[0])
            else:
                for seg in new_segments:
                    self._done_work_cache += float(seg)
            self._last_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        env = self.env
        now = env.elapsed_seconds
        gap = env.gap_seconds
        time_left = self.deadline - now

        self._update_done_cache()
        done = self._done_work_cache
        remaining_work = max(self.task_duration - done, 0.0)

        if remaining_work <= 0 or time_left <= 0:
            return ClusterType.NONE

        if self._use_od_only:
            return ClusterType.ON_DEMAND

        padding = self.PADDING_SECONDS

        # Check if it's safe to allow one more step that might yield zero progress.
        min_time_needed_after_delay = remaining_work + self.restart_overhead + padding + gap

        if min_time_needed_after_delay > time_left:
            # No more slack for potential wasted time: switch to OD permanently.
            self._use_od_only = True
            return ClusterType.ON_DEMAND

        # Risk-tolerant mode: use spot when available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser) -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)