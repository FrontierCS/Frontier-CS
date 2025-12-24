import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _compute_done_work(task_done_time: Any) -> float:
    if not task_done_time:
        return 0.0
    total = 0.0
    try:
        for seg in task_done_time:
            if seg is None:
                continue
            if isinstance(seg, (int, float)):
                total += float(seg)
                continue
            if isinstance(seg, dict):
                if "duration" in seg:
                    total += _safe_float(seg.get("duration"), 0.0)
                    continue
                if "start" in seg and "end" in seg:
                    total += max(0.0, _safe_float(seg.get("end"), 0.0) - _safe_float(seg.get("start"), 0.0))
                    continue
                if "done" in seg:
                    total += _safe_float(seg.get("done"), 0.0)
                    continue
                continue
            if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                a = _safe_float(seg[0], 0.0)
                b = _safe_float(seg[1], 0.0)
                total += max(0.0, b - a)
                continue
            if hasattr(seg, "duration"):
                total += _safe_float(getattr(seg, "duration", 0.0), 0.0)
                continue
            if hasattr(seg, "start") and hasattr(seg, "end"):
                total += max(0.0, _safe_float(getattr(seg, "end", 0.0), 0.0) - _safe_float(getattr(seg, "start", 0.0), 0.0))
                continue
    except Exception:
        try:
            return float(sum(task_done_time))  # type: ignore[arg-type]
        except Exception:
            return 0.0
    return float(total)


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._committed_od = False

        self._ema_avail = 0.20
        self._ema_alpha = 0.03

        self._prev_avail: Optional[bool] = None
        self._cur_avail_run_s = 0.0
        self._avg_avail_run_s: Optional[float] = None
        self._run_ema_beta = 0.10

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_availability_stats(self, has_spot: bool) -> None:
        self._ema_avail = (1.0 - self._ema_alpha) * self._ema_avail + self._ema_alpha * (1.0 if has_spot else 0.0)

        gap = _safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)

        if self._prev_avail is None:
            self._prev_avail = has_spot
            self._cur_avail_run_s = gap if has_spot else 0.0
            return

        if has_spot:
            if not self._prev_avail:
                self._cur_avail_run_s = gap
            else:
                self._cur_avail_run_s += gap
        else:
            if self._prev_avail and self._cur_avail_run_s > 0:
                if self._avg_avail_run_s is None:
                    self._avg_avail_run_s = self._cur_avail_run_s
                else:
                    self._avg_avail_run_s = (1.0 - self._run_ema_beta) * self._avg_avail_run_s + self._run_ema_beta * self._cur_avail_run_s
            self._cur_avail_run_s = 0.0

        self._prev_avail = has_spot

    def _should_avoid_starting_spot(self) -> bool:
        if self._avg_avail_run_s is None:
            return False
        ro = _safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        if ro <= 0:
            return False
        return (self._avg_avail_run_s < 1.1 * ro) and (self._ema_avail < 0.12)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_availability_stats(has_spot)

        elapsed = _safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        gap = _safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        deadline = _safe_float(getattr(self, "deadline", 0.0), 0.0)
        task_duration = _safe_float(getattr(self, "task_duration", 0.0), 0.0)
        ro = _safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        done_work = _compute_done_work(getattr(self, "task_done_time", None))
        remaining_work = max(0.0, task_duration - done_work)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_remaining = max(0.0, deadline - elapsed)

        if self._committed_od:
            return ClusterType.ON_DEMAND

        od_switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else ro

        safety_time = max(2.0 * gap, 0.5 * ro)
        safety_time = max(safety_time, 0.05 * 3600.0)

        required_if_od_now = remaining_work + od_switch_overhead
        if time_remaining <= required_if_od_now + safety_time:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            if not self._should_avoid_starting_spot():
                return ClusterType.SPOT
            return ClusterType.NONE

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
