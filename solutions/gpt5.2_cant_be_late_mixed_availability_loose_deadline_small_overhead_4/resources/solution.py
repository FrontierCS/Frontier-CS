import math
from collections import deque
from typing import Any, Deque, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "lazy_spot_with_deadline_guard"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self._history: Deque[bool] = deque()
        self._history_maxlen: int = 0
        self._last_has_spot: Optional[bool] = None

        self._done_sum: float = 0.0
        self._done_len: int = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _segment_value(self, seg: Any) -> float:
        try:
            if isinstance(seg, (int, float)):
                return float(seg)
            if isinstance(seg, (tuple, list)):
                if len(seg) == 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                    a = float(seg[0])
                    b = float(seg[1])
                    if b >= a:
                        return b - a
                    return a
                s = 0.0
                for x in seg:
                    if isinstance(x, (int, float)):
                        s += float(x)
                return s
        except Exception:
            return 0.0
        return 0.0

    def _get_done_work_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, list):
            return 0.0
        n = len(tdt)
        if n < self._done_len:
            total = 0.0
            for seg in tdt:
                total += self._segment_value(seg)
            self._done_sum = total
            self._done_len = n
            return total
        if n == self._done_len:
            return self._done_sum
        add = 0.0
        for i in range(self._done_len, n):
            add += self._segment_value(tdt[i])
        self._done_sum += add
        self._done_len = n
        return self._done_sum

    def _update_history(self, has_spot: bool):
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        target_window_seconds = 6.0 * 3600.0
        maxlen = max(30, int(target_window_seconds / max(gap, 1e-6)))
        if maxlen != self._history_maxlen:
            old = list(self._history)
            self._history = deque(old[-maxlen:], maxlen=maxlen)
            self._history_maxlen = maxlen
        if self._history.maxlen is None:
            self._history = deque(self._history, maxlen=maxlen)
            self._history_maxlen = maxlen

        self._history.append(bool(has_spot))
        self._last_has_spot = bool(has_spot)

    def _estimate_restart_rate(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        h = self._history
        if len(h) < 3:
            return 0.0
        starts = 0
        prev = h[0]
        for cur in list(h)[1:]:
            if (not prev) and cur:
                starts += 1
            prev = cur
        window_time = max(1e-6, len(h) * gap)
        return starts / window_time  # restarts per second (approx)

    def _estimate_p_lower(self) -> float:
        h = self._history
        n = len(h)
        if n <= 1:
            return 0.5
        s = sum(1 for x in h if x)
        p = s / n
        # Simple lower confidence bound
        sigma = math.sqrt(max(0.0, p * (1.0 - p) / n))
        return max(0.0, p - 1.0 * sigma)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_history(has_spot)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._get_done_work_seconds()
        remaining_work = max(0.0, task_duration - done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_remaining = max(0.0, deadline - elapsed)
        if time_remaining <= 0.0:
            return ClusterType.NONE

        slack = time_remaining - remaining_work

        # Safety buffer to account for discretization + restart overhead + estimated future restarts
        buffer_base = max(2.0 * restart_overhead, 2.0 * gap) + 10.0 * 60.0  # 10 minutes
        restart_rate = self._estimate_restart_rate()
        expected_restarts = restart_rate * time_remaining
        expected_overhead = expected_restarts * restart_overhead
        safety = buffer_base + 1.5 * expected_overhead

        # If slack is very tight, switch to guaranteed compute.
        if slack <= safety:
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available; pause when not.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable; decide whether to wait or use on-demand.
        # If slack is still ample, wait; else use on-demand.
        p_lower = self._estimate_p_lower()
        # If spot is likely very scarce, keep a smaller waiting cushion
        scarce_adjust = (1.0 - p_lower) * (30.0 * 60.0)  # up to +30 min cushion when scarce
        wait_floor = buffer_base + scarce_adjust

        if slack > wait_floor:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
