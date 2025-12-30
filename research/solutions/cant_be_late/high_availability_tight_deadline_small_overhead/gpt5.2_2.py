from __future__ import annotations

import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self.args = args

        self._committed_od: bool = False

        self._last_has_spot: Optional[bool] = None
        self._streak_len_s: float = 0.0

        self._mean_up_s: Optional[float] = None
        self._mean_down_s: Optional[float] = None
        self._ema_p: float = 0.70

        self._consec_spot: int = 0
        self._consec_no_spot: int = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _ema(prev: Optional[float], new: float, alpha: float) -> float:
        if prev is None or not math.isfinite(prev):
            return float(new)
        return float(prev) * (1.0 - alpha) + float(new) * alpha

    def _gap_s(self) -> float:
        try:
            g = float(getattr(self.env, "gap_seconds", 60.0))
            if g > 0:
                return g
        except Exception:
            pass
        return 60.0

    def _update_spot_stats(self, has_spot: bool) -> None:
        gap = self._gap_s()
        alpha = 0.12
        beta = 0.03

        self._ema_p = (1.0 - beta) * self._ema_p + beta * (1.0 if has_spot else 0.0)

        if has_spot:
            self._consec_spot += 1
            self._consec_no_spot = 0
        else:
            self._consec_no_spot += 1
            self._consec_spot = 0

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            self._streak_len_s = gap
        else:
            if has_spot == self._last_has_spot:
                self._streak_len_s += gap
            else:
                ended = max(gap, self._streak_len_s)
                if self._last_has_spot:
                    self._mean_up_s = self._ema(self._mean_up_s, ended, alpha)
                else:
                    self._mean_down_s = self._ema(self._mean_down_s, ended, alpha)
                self._last_has_spot = has_spot
                self._streak_len_s = gap

        base_default = 1800.0
        if self._mean_up_s is None:
            self._mean_up_s = base_default
        if self._mean_down_s is None:
            self._mean_down_s = base_default

    def _work_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0

        if isinstance(tdt, (int, float)):
            v = float(tdt)
            return 0.0 if not math.isfinite(v) else max(0.0, v)

        if isinstance(tdt, (list, tuple)):
            if not tdt:
                return 0.0

            total = 0.0
            numeric_count = 0
            for x in tdt:
                if x is None:
                    continue
                if isinstance(x, (int, float)):
                    v = float(x)
                    if math.isfinite(v):
                        total += v
                        numeric_count += 1
                elif isinstance(x, (list, tuple)) and len(x) >= 2:
                    a, b = x[0], x[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        a = float(a)
                        b = float(b)
                        if math.isfinite(a) and math.isfinite(b):
                            total += max(0.0, b - a)
                elif isinstance(x, dict):
                    if "duration" in x and isinstance(x["duration"], (int, float)):
                        v = float(x["duration"])
                        if math.isfinite(v):
                            total += max(0.0, v)
                    elif "start" in x and "end" in x:
                        try:
                            a = float(x["start"])
                            b = float(x["end"])
                            if math.isfinite(a) and math.isfinite(b):
                                total += max(0.0, b - a)
                        except Exception:
                            pass
                else:
                    try:
                        v = float(x)
                        if math.isfinite(v):
                            total += v
                            numeric_count += 1
                    except Exception:
                        pass

            if total > 0.0:
                return total

            last = tdt[-1]
            if isinstance(last, (int, float)):
                v = float(last)
                return 0.0 if not math.isfinite(v) else max(0.0, v)

        return 0.0

    def _remaining_work_seconds(self) -> float:
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        if not math.isfinite(td) or td <= 0:
            return 0.0
        done = self._work_done_seconds()
        if not math.isfinite(done):
            done = 0.0
        return max(0.0, td - done)

    def _time_remaining_seconds(self) -> float:
        d = float(getattr(self, "deadline", 0.0) or 0.0)
        e = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        if not (math.isfinite(d) and math.isfinite(e)):
            return 0.0
        return max(0.0, d - e)

    def _expected_down_remaining_seconds(self) -> float:
        gap = self._gap_s()
        md = float(self._mean_down_s) if self._mean_down_s is not None else 1800.0
        if md < gap:
            md = gap
        if self._last_has_spot is False:
            rem = md - float(self._streak_len_s)
            return max(gap, rem)
        return md

    def _reserve_seconds(self, last_cluster_type: ClusterType) -> float:
        gap = self._gap_s()
        restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        restart = restart if math.isfinite(restart) and restart > 0 else 0.0

        base = max(3.0 * gap, 6.0 * restart, 600.0)

        md = float(self._mean_down_s) if self._mean_down_s is not None else 1800.0
        md = max(gap, md)

        p = min(0.98, max(0.02, float(self._ema_p)))
        extra = (1.0 - p) * min(7200.0, md + 3600.0)

        if last_cluster_type == ClusterType.SPOT:
            extra += 2.0 * restart + 1.0 * gap

        return base + extra

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not has_spot and last_cluster_type == ClusterType.SPOT:
            pass

        self._update_spot_stats(bool(has_spot))

        W = self._remaining_work_seconds()
        if W <= 0.0:
            return ClusterType.NONE

        T = self._time_remaining_seconds()
        if T <= 0.0:
            return ClusterType.NONE

        restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        restart = restart if math.isfinite(restart) and restart > 0 else 0.0

        reserve = self._reserve_seconds(last_cluster_type)

        overhead_start_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart
        if T <= W + overhead_start_od + reserve:
            self._committed_od = True

        if self._committed_od:
            return ClusterType.ON_DEMAND

        slack = T - W

        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT

            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._consec_spot < 2 and slack < 2.0 * reserve:
                    return ClusterType.ON_DEMAND

                mu = float(self._mean_up_s) if self._mean_up_s is not None else 1800.0
                mu = max(self._gap_s(), mu)
                min_up = max(3.0 * self._gap_s(), 10.0 * restart, 900.0)

                if mu < min_up and slack < 4.0 * reserve:
                    return ClusterType.ON_DEMAND

                if T <= W + overhead_start_od + 1.5 * reserve:
                    return ClusterType.ON_DEMAND

                return ClusterType.SPOT

            if last_cluster_type == ClusterType.NONE:
                if T <= W + restart + reserve:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            return ClusterType.SPOT

        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        expected_down_rem = self._expected_down_remaining_seconds()
        if slack > expected_down_rem + reserve:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)