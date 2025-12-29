import json
import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbll_ewma_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self.args = args

        self._initialized = False
        self._last_has_spot: Optional[bool] = None

        self._beta = 0.06
        self._p_off_on = 0.25
        self._p_on_off = 0.10

        self._consec_on = 0
        self._consec_off = 0

        self._lock_od_until = 0.0

        self._done_cache_kind: Optional[str] = None
        self._done_cache_len = -1
        self._done_cache_value = 0.0

    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, "r") as f:
                spec = json.load(f)
            if isinstance(spec, dict):
                beta = spec.get("beta", None)
                if isinstance(beta, (int, float)) and 0.0 < float(beta) <= 1.0:
                    self._beta = float(beta)
        except Exception:
            pass
        return self

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _get_done_work_seconds(self) -> float:
        v = getattr(self.env, "task_done_seconds", None)
        if self._is_number(v):
            return float(v)

        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if self._is_number(tdt):
            return float(tdt)

        if not isinstance(tdt, (list, tuple)):
            return 0.0

        n = len(tdt)
        if n == 0:
            self._done_cache_len = 0
            self._done_cache_value = 0.0
            return 0.0

        kind = self._done_cache_kind
        if kind is None:
            first = tdt[0]
            if self._is_number(first):
                kind = "numbers"
            elif isinstance(first, (list, tuple)) and len(first) >= 2 and self._is_number(first[0]) and self._is_number(first[1]):
                kind = "intervals"
            else:
                kind = "unknown"
            self._done_cache_kind = kind

        if kind == "numbers":
            if n >= self._done_cache_len >= 0:
                inc = 0.0
                for x in tdt[self._done_cache_len : n]:
                    if self._is_number(x):
                        inc += float(x)
                    else:
                        self._done_cache_len = -1
                        self._done_cache_value = 0.0
                        self._done_cache_kind = "unknown"
                        return self._get_done_work_seconds()
                self._done_cache_value += inc
                self._done_cache_len = n

                td = float(getattr(self, "task_duration", 0.0) or 0.0)
                if td > 0.0 and self._done_cache_value > td * 1.5:
                    is_mono = True
                    prev = float(tdt[0]) if self._is_number(tdt[0]) else None
                    if prev is None:
                        is_mono = False
                    else:
                        for x in tdt[1:]:
                            if not self._is_number(x):
                                is_mono = False
                                break
                            fx = float(x)
                            if fx < prev:
                                is_mono = False
                                break
                            prev = fx
                    if is_mono and self._is_number(tdt[-1]):
                        lastv = float(tdt[-1])
                        if 0.0 <= lastv <= td * 1.05:
                            self._done_cache_value = lastv
                return self._done_cache_value
            else:
                s = 0.0
                for x in tdt:
                    if self._is_number(x):
                        s += float(x)
                self._done_cache_len = n
                self._done_cache_value = s
                return s

        if kind == "intervals":
            if n == self._done_cache_len and self._done_cache_len >= 0:
                return self._done_cache_value
            s = 0.0
            for seg in tdt:
                if isinstance(seg, (list, tuple)) and len(seg) >= 2 and self._is_number(seg[0]) and self._is_number(seg[1]):
                    a = float(seg[0])
                    b = float(seg[1])
                    if b >= a:
                        s += (b - a)
                    else:
                        s += b
            self._done_cache_len = n
            self._done_cache_value = s
            return s

        s = 0.0
        for x in tdt:
            if self._is_number(x):
                s += float(x)
            elif isinstance(x, (list, tuple)) and len(x) >= 2 and self._is_number(x[0]) and self._is_number(x[1]):
                a = float(x[0])
                b = float(x[1])
                s += (b - a) if b >= a else b
        self._done_cache_len = n
        self._done_cache_value = s
        return s

    def _update_spot_model(self, has_spot: bool) -> None:
        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            self._consec_on = 1 if has_spot else 0
            self._consec_off = 0 if has_spot else 1
            return

        if self._last_has_spot:
            obs = 1.0 if (not has_spot) else 0.0
            self._p_on_off = (1.0 - self._beta) * self._p_on_off + self._beta * obs
        else:
            obs = 1.0 if has_spot else 0.0
            self._p_off_on = (1.0 - self._beta) * self._p_off_on + self._beta * obs

        self._last_has_spot = has_spot
        if has_spot:
            self._consec_on += 1
            self._consec_off = 0
        else:
            self._consec_off += 1
            self._consec_on = 0

        self._p_on_off = min(max(self._p_on_off, 1e-4), 0.999)
        self._p_off_on = min(max(self._p_off_on, 1e-4), 0.999)

    def _expected_on_run_seconds(self, dt: float) -> float:
        steps = 1.0 / max(self._p_on_off, 1e-3)
        base = steps * dt
        if self._consec_on > 0:
            base = max(base, self._consec_on * dt)
        return min(base, 24.0 * 3600.0)

    def _expected_off_wait_seconds(self, dt: float) -> float:
        steps = 1.0 / max(self._p_off_on, 1e-3)
        base = steps * dt
        if self._consec_off > 0:
            base = max(base, 0.5 * self._consec_off * dt)
        return min(base, 24.0 * 3600.0)

    def _set_od_lock(self, seconds: float) -> None:
        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        self._lock_od_until = max(self._lock_od_until, now + max(0.0, float(seconds)))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._initialized = True
            self._last_has_spot = None
            self._consec_on = 0
            self._consec_off = 0

        self._update_spot_model(bool(has_spot))

        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        dt = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        dt = max(dt, 1.0)

        done = self._get_done_work_seconds()
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        remaining = max(0.0, td - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, deadline - now)
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        start_od_overhead = 0.0 if (last_cluster_type == ClusterType.ON_DEMAND) else ro
        min_od_time = remaining + start_od_overhead

        if min_od_time >= time_left - 1e-9:
            self._set_od_lock(time_left)
            return ClusterType.ON_DEMAND

        slack_after_start_od = time_left - min_od_time

        if slack_after_start_od <= max(1.10 * ro, 1.5 * dt):
            self._set_od_lock(max(3600.0, 6.0 * ro))

        if now < self._lock_od_until:
            return ClusterType.ON_DEMAND

        if not has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND

            exp_wait = self._expected_off_wait_seconds(dt)
            risk_buf = max(2.0 * ro, 0.5 * 3600.0)

            if slack_after_start_od >= exp_wait + risk_buf:
                return ClusterType.NONE

            if exp_wait <= 2.0 * dt and slack_after_start_od >= (dt + 1.5 * ro):
                return ClusterType.NONE

            lock_dur = max(3600.0, 8.0 * ro)
            if slack_after_start_od < 2.0 * 3600.0:
                lock_dur = max(lock_dur, 2.0 * 3600.0)
            self._set_od_lock(lock_dur)
            return ClusterType.ON_DEMAND

        if slack_after_start_od <= max(1.25 * ro, 2.0 * dt):
            self._set_od_lock(max(3600.0, 6.0 * ro))
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            exp_run = self._expected_on_run_seconds(dt)
            min_run = max(3.0 * ro, 6.0 * dt)

            if exp_run >= min_run and slack_after_start_od >= (2.0 * ro + dt):
                return ClusterType.SPOT

            if slack_after_start_od >= 6.0 * ro and exp_run >= 3.0 * dt:
                return ClusterType.SPOT

            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)