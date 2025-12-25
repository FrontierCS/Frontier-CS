import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_latest_od_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            super().__init__()
        self._reset_run_state()

    def _reset_run_state(self) -> None:
        self._last_elapsed_seconds = -1.0
        self._done_seconds = 0.0
        self._done_idx = 0

    def solve(self, spec_path: str) -> "Solution":
        self._reset_run_state()
        return self

    @staticmethod
    def _parse_done_item(item: Any) -> float:
        try:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                a, b = item
                a = float(a)
                b = float(b)
                if b >= a:
                    return b - a
                return b
            return float(item)
        except Exception:
            return 0.0

    def _update_done_seconds(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if not lst:
            self._done_seconds = 0.0
            self._done_idx = 0
            return 0.0

        try:
            n = len(lst)
        except Exception:
            self._done_seconds = 0.0
            self._done_idx = 0
            return 0.0

        if n < self._done_idx:
            self._done_seconds = 0.0
            self._done_idx = 0

        while self._done_idx < n:
            self._done_seconds += self._parse_done_item(lst[self._done_idx])
            self._done_idx += 1

        if self._done_seconds < 0:
            self._done_seconds = 0.0

        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        if td > 0 and self._done_seconds > td:
            self._done_seconds = td
        return self._done_seconds

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)

        if self._last_elapsed_seconds >= 0.0 and elapsed + 1e-9 < self._last_elapsed_seconds:
            self._reset_run_state()
        self._last_elapsed_seconds = elapsed

        done = self._update_done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        work_left = task_duration - done
        if work_left <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        hard_margin = restart_overhead + 6.0 * gap + 120.0

        if time_left <= work_left + hard_margin:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)