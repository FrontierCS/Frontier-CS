from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:
        def __init__(self, args=None):
            self.args = args
            self.env = None


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _sum_work_done(task_done_time: Any) -> float:
    if task_done_time is None:
        return 0.0
    if isinstance(task_done_time, (int, float)):
        return float(task_done_time)
    if not isinstance(task_done_time, (list, tuple)):
        return 0.0
    total = 0.0
    for seg in task_done_time:
        if isinstance(seg, (int, float)):
            total += float(seg)
        elif isinstance(seg, (list, tuple)):
            if len(seg) == 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                a = float(seg[0])
                b = float(seg[1])
                if b >= a:
                    total += (b - a)
            elif len(seg) == 1 and isinstance(seg[0], (int, float)):
                total += float(seg[0])
    return total


@dataclass
class _Params:
    hist_window_seconds: float = 6 * 3600.0
    prior_alpha: float = 6.0
    prior_beta: float = 4.0
    conservative_margin: float = 0.15
    min_p: float = 0.05
    max_p: float = 0.98
    final_guard_overhead_mult: float = 2.5
    final_guard_gap_mult: float = 2.0
    od_lock_seconds: float = 30 * 60.0
    spot_to_od_slack_overhead_mult: float = 3.0


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._params = _Params()
        self._hist: Optional[Deque[int]] = None
        self._hist_sum: int = 0
        self._gap_seconds: Optional[float] = None
        self._od_lock_until: float = -1.0
        self._committed_od: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _ensure_hist(self) -> None:
        gap = getattr(self.env, "gap_seconds", None)
        if gap is None:
            return
        gap = float(gap)
        if self._hist is not None and self._gap_seconds == gap:
            return
        self._gap_seconds = gap
        maxlen = max(10, int(self._params.hist_window_seconds / max(gap, 1e-6)))
        self._hist = deque(maxlen=maxlen)
        self._hist_sum = 0
        self._od_lock_until = -1.0
        self._committed_od = False

    def _update_hist(self, has_spot: bool) -> None:
        if self._hist is None:
            return
        v = 1 if has_spot else 0
        if len(self._hist) == self._hist.maxlen:
            self._hist_sum -= self._hist[0]
        self._hist.append(v)
        self._hist_sum += v

    def _spot_prob_est(self) -> float:
        if self._hist is None or len(self._hist) == 0:
            return 0.60
        n = len(self._hist)
        a = self._params.prior_alpha + self._hist_sum
        b = self._params.prior_beta + (n - self._hist_sum)
        p = a / (a + b)
        if p < self._params.min_p:
            p = self._params.min_p
        if p > self._params.max_p:
            p = self._params.max_p
        return p

    def _work_done_seconds(self) -> float:
        return _sum_work_done(getattr(self, "task_done_time", None))

    def _remaining_work_seconds(self) -> float:
        dur = _as_float(getattr(self, "task_duration", 0.0), 0.0)
        done = self._work_done_seconds()
        rem = dur - done
        return rem if rem > 0.0 else 0.0

    def _deadline_seconds(self) -> float:
        return _as_float(getattr(self, "deadline", 0.0), 0.0)

    def _restart_overhead_seconds(self) -> float:
        return _as_float(getattr(self, "restart_overhead", 0.0), 0.0)

    def _elapsed_seconds(self) -> float:
        return _as_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)

    def _remaining_time_seconds(self) -> float:
        return max(0.0, self._deadline_seconds() - self._elapsed_seconds())

    def _final_guard_seconds(self) -> float:
        oh = self._restart_overhead_seconds()
        gap = _as_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        return self._params.final_guard_overhead_mult * oh + self._params.final_guard_gap_mult * gap

    def _should_commit_od_now(self, remaining_work: float, remaining_time: float) -> bool:
        if remaining_work <= 0.0:
            return False
        guard = self._final_guard_seconds()
        if remaining_time <= remaining_work + guard:
            return True
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_hist()
        self._update_hist(has_spot)

        remaining_work = self._remaining_work_seconds()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_time = self._remaining_time_seconds()
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND if has_spot is False else ClusterType.ON_DEMAND

        elapsed = self._elapsed_seconds()
        oh = self._restart_overhead_seconds()

        if self._committed_od or self._should_commit_od_now(remaining_work, remaining_time):
            self._committed_od = True
            self._od_lock_until = float("inf")
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work  # seconds of "spare" time if on guaranteed compute from now

        p = self._spot_prob_est()
        p_low = max(self._params.min_p, min(self._params.max_p, p - self._params.conservative_margin))
        required_rate = remaining_work / max(1e-9, remaining_time)

        if last_cluster_type == ClusterType.ON_DEMAND and elapsed < self._od_lock_until:
            return ClusterType.ON_DEMAND

        if has_spot:
            if required_rate > 0.95 and slack <= self._params.spot_to_od_slack_overhead_mult * oh:
                self._od_lock_until = elapsed + self._params.od_lock_seconds
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        if required_rate > p_low or slack <= self._params.spot_to_od_slack_overhead_mult * oh:
            self._od_lock_until = elapsed + self._params.od_lock_seconds
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)