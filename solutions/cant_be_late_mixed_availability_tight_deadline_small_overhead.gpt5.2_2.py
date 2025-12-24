import math
from collections import deque

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False
        self._avail_window = None
        self._avail_sum = 0
        self._ewma_p = 0.5
        self._ewma_alpha = 0.02

        self._consec_spot = 0
        self._spot_stable_steps = 1

        self._od_lock_until = -1.0
        self._od_lock_seconds = 0.0

        self._last_elapsed = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _safe_float(x, default=None):
        try:
            return float(x)
        except Exception:
            return default

    def _work_done(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            return 0.0

        try:
            first = td[0]
        except Exception:
            return 0.0

        # Segments as (start, end)
        if isinstance(first, (tuple, list)) and len(first) == 2:
            total = 0.0
            for seg in td:
                try:
                    a, b = seg
                    a = float(a)
                    b = float(b)
                    if b > a:
                        total += (b - a)
                except Exception:
                    continue
            return max(0.0, total)

        # Numeric list: could be cumulative or per-step increments
        if all(isinstance(x, (int, float)) for x in td):
            if len(td) == 1:
                v = float(td[0])
                return max(0.0, min(v, float(getattr(self, "task_duration", v))))
            monotonic = True
            for i in range(1, len(td)):
                if td[i] < td[i - 1]:
                    monotonic = False
                    break
            task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
            if monotonic:
                last = float(td[-1])
                if task_dur > 0 and last <= task_dur * 1.05:
                    return max(0.0, min(last, task_dur))
                return max(0.0, last)
            total = float(sum(td))
            if task_dur > 0:
                total = min(total, task_dur)
            return max(0.0, total)

        # Fallback: try last element as float
        v = self._safe_float(td[-1], default=0.0)
        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        if task_dur > 0:
            v = min(v, task_dur)
        return max(0.0, v)

    def _ensure_init(self):
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        gap = max(1.0, gap)

        # Use ~3 hours of history, bounded.
        target_window_seconds = 3.0 * 3600.0
        n = int(target_window_seconds / gap)
        n = max(60, min(2500, n))
        self._avail_window = deque(maxlen=n)
        self._avail_sum = 0

        self._ewma_alpha = 2.0 / (n + 1.0)

        # Require spot to be stable for ~5 minutes before switching from OD -> SPOT.
        stable_seconds = 5.0 * 60.0
        self._spot_stable_steps = max(1, int(stable_seconds / gap))

        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        self._od_lock_seconds = max(15.0 * 60.0, 10.0 * ro, 3.0 * gap)

        self._initialized = True

    def _update_availability_stats(self, has_spot: bool):
        v = 1 if has_spot else 0

        if self._avail_window is not None:
            if len(self._avail_window) == self._avail_window.maxlen:
                old = self._avail_window[0]
                self._avail_sum -= old
            self._avail_window.append(v)
            self._avail_sum += v

        self._ewma_p = (1.0 - self._ewma_alpha) * self._ewma_p + self._ewma_alpha * float(v)

        if has_spot:
            self._consec_spot += 1
        else:
            self._consec_spot = 0

    def _p_conservative(self) -> float:
        if not self._avail_window or len(self._avail_window) == 0:
            p = self._ewma_p
            return max(0.02, min(1.0, 0.85 * p))

        n = len(self._avail_window)
        phat = self._avail_sum / float(n)
        p_est = 0.5 * phat + 0.5 * self._ewma_p

        # Conservative lower bound: subtract confidence + small bias
        var = max(p_est * (1.0 - p_est), 1e-9)
        se = math.sqrt(var / max(1.0, float(n)))
        lower = p_est - 1.5 * se - 0.02

        # Clamp and enforce small minimum to avoid pathological behavior
        lower = max(0.0, min(1.0, lower))
        return max(0.02, lower)

    def _start_od_lock(self, now: float):
        self._od_lock_until = max(self._od_lock_until, now + self._od_lock_seconds)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        gap = max(1.0, gap)

        # Update availability stats with current observation
        self._update_availability_stats(has_spot)

        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._work_done()
        remaining_work = max(0.0, task_dur - done)
        remaining_time = deadline - now

        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If we are (almost) out of slack, commit to on-demand.
        buffer = max(4.0 * ro, 10.0 * gap, 10.0 * 60.0)
        if remaining_time <= remaining_work + buffer:
            self._start_od_lock(now)
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work
        if slack <= max(6.0 * ro, 30.0 * 60.0):
            self._start_od_lock(now)
            return ClusterType.ON_DEMAND

        p_cons = self._p_conservative()
        # Reserve buffer time (for overhead / uncertainty) from future spot estimate
        effective_time = max(0.0, remaining_time - buffer)
        expected_spot_work = p_cons * effective_time
        need_od = remaining_work - expected_spot_work

        if has_spot:
            # If we're locked to OD, or spot hasn't been stable, stay on OD.
            if now < self._od_lock_until:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.ON_DEMAND and self._consec_spot < self._spot_stable_steps:
                # If we don't have lots of slack, avoid thrashing.
                if slack < max(2.0 * 3600.0, 20.0 * ro):
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot unavailable
        if need_od > 0.0:
            self._start_od_lock(now)
            return ClusterType.ON_DEMAND

        # If no OD is (conservatively) needed, idle to save cost.
        # Avoid idling when slack isn't comfortable.
        if slack > max(2.0 * 3600.0, 20.0 * ro):
            return ClusterType.NONE

        # Small slack: keep making progress
        self._start_od_lock(now)
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
