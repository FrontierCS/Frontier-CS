import math
from collections import deque
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
        def __init__(self, *args, **kwargs):
            self.env = None


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self.args = args

        self._inited = False
        self._gap = 60.0

        # Availability tracking
        self._prev_has_spot: Optional[bool] = None
        self._streak_is_avail: Optional[bool] = None
        self._streak_len_sec: float = 0.0
        self._ema_avail_dur_sec: float = 3600.0
        self._ema_unavail_dur_sec: float = 900.0
        self._ema_alpha: float = 0.06

        self._spot_hist: Deque[int] = deque()
        self._spot_hist_maxlen: int = 720  # set on init based on gap

        # Progress tracking
        self._done_len: int = 0
        self._done_sum: float = 0.0

        # Switching/locking to avoid oscillation
        self._lock_cluster: Optional[ClusterType] = None
        self._lock_until_elapsed: float = 0.0
        self._min_od_lock_sec: float = 1800.0
        self._min_spot_lock_sec: float = 600.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _update_done_sum(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, list):
            return 0.0

        n = len(tdt)
        if n == self._done_len:
            return self._done_sum

        s = self._done_sum
        start_idx = self._done_len
        if n < self._done_len:
            s = 0.0
            start_idx = 0

        for i in range(start_idx, n):
            x = tdt[i]
            if self._is_number(x):
                s += float(x)
                continue
            if isinstance(x, (tuple, list)) and len(x) >= 2 and self._is_number(x[0]) and self._is_number(x[1]):
                a = float(x[0])
                b = float(x[1])
                if b >= a:
                    s += (b - a)
                else:
                    s += a
                continue
            dur = getattr(x, "duration", None)
            if self._is_number(dur):
                s += float(dur)
                continue
            val = getattr(x, "done_seconds", None)
            if self._is_number(val):
                s += float(val)
                continue

        self._done_len = n
        self._done_sum = s
        return s

    def _init_if_needed(self):
        if self._inited:
            return
        gap = getattr(getattr(self, "env", None), "gap_seconds", None)
        if self._is_number(gap) and gap > 0:
            self._gap = float(gap)
        else:
            self._gap = 60.0

        # History window: ~6 hours of data, capped
        self._spot_hist_maxlen = int(max(60, min(4000, round((6.0 * 3600.0) / max(1.0, self._gap)))))
        self._spot_hist = deque(maxlen=self._spot_hist_maxlen)

        # Locks scaled by gap
        self._min_od_lock_sec = max(900.0, min(5400.0, 30.0 * 60.0))
        self._min_spot_lock_sec = max(2.0 * self._gap, min(1800.0, 10.0 * 60.0))

        self._inited = True

    def _update_availability_stats(self, has_spot: bool):
        self._spot_hist.append(1 if has_spot else 0)

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._streak_is_avail = has_spot
            self._streak_len_sec = self._gap
            return

        if has_spot == self._prev_has_spot:
            self._streak_len_sec += self._gap
            return

        # Close previous streak
        prev_len = max(self._gap, self._streak_len_sec)
        if self._streak_is_avail:
            self._ema_avail_dur_sec = self._ema_alpha * prev_len + (1.0 - self._ema_alpha) * self._ema_avail_dur_sec
        else:
            self._ema_unavail_dur_sec = self._ema_alpha * prev_len + (1.0 - self._ema_alpha) * self._ema_unavail_dur_sec

        self._prev_has_spot = has_spot
        self._streak_is_avail = has_spot
        self._streak_len_sec = self._gap

    def _spot_availability_prob(self) -> float:
        if not self._spot_hist:
            return 0.5
        return sum(self._spot_hist) / float(len(self._spot_hist))

    def _apply_lock(self, elapsed: float, last_cluster_type: ClusterType, desired: ClusterType, has_spot: bool) -> ClusterType:
        if self._lock_cluster is not None and elapsed < self._lock_until_elapsed and last_cluster_type == self._lock_cluster:
            if self._lock_cluster == ClusterType.SPOT:
                return ClusterType.SPOT if has_spot else desired
            return self._lock_cluster

        # If desired is SPOT but not available, it must be corrected by caller; do a last check.
        if desired == ClusterType.SPOT and not has_spot:
            desired = ClusterType.ON_DEMAND

        if desired != last_cluster_type:
            if desired == ClusterType.ON_DEMAND:
                self._lock_cluster = ClusterType.ON_DEMAND
                self._lock_until_elapsed = elapsed + self._min_od_lock_sec
            elif desired == ClusterType.SPOT:
                self._lock_cluster = ClusterType.SPOT
                self._lock_until_elapsed = elapsed + self._min_spot_lock_sec
            else:
                self._lock_cluster = None
                self._lock_until_elapsed = 0.0

        return desired

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()
        self._update_availability_stats(bool(has_spot))

        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", self._gap) or self._gap)
        if gap > 0:
            self._gap = gap

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._update_done_sum()
        remaining = max(0.0, task_duration - done)

        if remaining <= 1e-9:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        required_frac = remaining / max(1.0, time_left)
        slack = time_left - remaining

        p_hat = self._spot_availability_prob()
        avail_dur = max(self._gap, float(self._ema_avail_dur_sec))
        unavail_dur = max(self._gap, float(self._ema_unavail_dur_sec))

        # Approximate effective progress rate if using spot-only with restarts per availability streak
        overhead_ratio = restart_overhead / max(restart_overhead + self._gap, avail_dur)
        eff_rate_spot_only = p_hat * max(0.0, 1.0 - overhead_ratio)

        safety = 2.0 * restart_overhead + 4.0 * self._gap
        urgent = slack < safety or required_frac > 0.97
        spot_too_choppy = avail_dur < 1.2 * max(self._gap, restart_overhead)

        if spot_too_choppy and required_frac > 0.60:
            urgent = True

        # Decide mode
        if urgent:
            desired = ClusterType.ON_DEMAND
        else:
            # If spot-only likely sufficient and we have comfortable slack, prefer waiting over OD during outages
            spot_only_ok = eff_rate_spot_only >= required_frac * 1.05 and p_hat >= 0.18 and not spot_too_choppy
            if spot_only_ok:
                if has_spot:
                    desired = ClusterType.SPOT
                else:
                    # Wait if slack can absorb a typical outage + cushion; otherwise run OD
                    wait_cushion = max(safety, 2.0 * unavail_dur, 3600.0)
                    desired = ClusterType.NONE if slack > wait_cushion else ClusterType.ON_DEMAND
            else:
                # Hybrid: use OD during outages, use spot when available only if streaks likely long enough
                if has_spot and not spot_too_choppy and slack > (restart_overhead + 2.0 * self._gap):
                    # Avoid switching from OD->SPOT if near deadline or spot streaks are short
                    if last_cluster_type == ClusterType.ON_DEMAND:
                        remaining_avail_expect = max(0.0, avail_dur - (self._streak_len_sec if self._streak_is_avail else 0.0))
                        remaining_avail_expect = max(0.5 * avail_dur, remaining_avail_expect)
                        switch_ok = (
                            slack > (2.5 * restart_overhead + 6.0 * self._gap)
                            and remaining_avail_expect > (3.0 * restart_overhead + 3.0 * self._gap)
                            and p_hat > 0.25
                        )
                        desired = ClusterType.SPOT if switch_ok else ClusterType.ON_DEMAND
                    else:
                        desired = ClusterType.SPOT
                else:
                    desired = ClusterType.ON_DEMAND

        if desired == ClusterType.SPOT and not has_spot:
            desired = ClusterType.ON_DEMAND

        # Avoid switching SPOT->OD unless urgent or spot unavailable
        if last_cluster_type == ClusterType.SPOT and has_spot and desired == ClusterType.ON_DEMAND and not urgent:
            desired = ClusterType.SPOT

        # If NONE while spot is available, just use spot
        if desired == ClusterType.NONE and has_spot:
            desired = ClusterType.SPOT

        return self._apply_lock(elapsed, last_cluster_type, desired, has_spot)

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
