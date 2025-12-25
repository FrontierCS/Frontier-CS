import math
import numbers
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._locked_od = False
        self._tdt_mode: Optional[str] = None
        self._tdt_len = 0
        self._tdt_cum = 0.0
        self._last_done = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _is_num(x: Any) -> bool:
        return isinstance(x, numbers.Real) and not isinstance(x, bool)

    @classmethod
    def _to_float(cls, x: Any) -> Optional[float]:
        if cls._is_num(x):
            return float(x)
        try:
            return float(x)
        except Exception:
            return None

    def _infer_tdt_mode(self, tdt) -> str:
        # Returns one of: cumulative_numeric, durations_numeric, segments, dict_cumulative, dict_duration
        if not isinstance(tdt, (list, tuple)) or len(tdt) == 0:
            return "cumulative_numeric"

        last = tdt[-1]

        if isinstance(last, dict):
            if "done" in last or "cumulative" in last or "progress" in last:
                return "dict_cumulative"
            if "duration" in last:
                return "dict_duration"
            if "start" in last and "end" in last:
                return "segments"
            return "dict_cumulative"

        if isinstance(last, (list, tuple)) and len(last) >= 2:
            a = self._to_float(last[0])
            b = self._to_float(last[1])
            if a is not None and b is not None:
                return "segments"

        if self._is_num(last):
            m = min(len(tdt), 10)
            ok = True
            prev = None
            for x in tdt[-m:]:
                v = self._to_float(x)
                if v is None:
                    ok = False
                    break
                if prev is not None and v + 1e-12 < prev:
                    ok = False
                    break
                prev = v
            if ok:
                return "cumulative_numeric"
            return "durations_numeric"

        return "cumulative_numeric"

    def _extract_done(self) -> float:
        td = getattr(self, "task_duration", 0.0) or 0.0
        tdt = getattr(self, "task_done_time", None)

        if tdt is None:
            return self._last_done

        # Numeric scalar
        if self._is_num(tdt):
            v = float(tdt)
            if v > self._last_done:
                self._last_done = v
            if td > 0:
                self._last_done = min(self._last_done, td)
            return self._last_done

        # Convert arrays to list if possible
        if not isinstance(tdt, (list, tuple)):
            try:
                tdt = list(tdt)
            except Exception:
                return self._last_done

        n = len(tdt)
        if n == 0:
            return self._last_done

        if n < self._tdt_len:
            self._tdt_mode = None
            self._tdt_len = 0
            self._tdt_cum = 0.0

        if self._tdt_mode is None:
            self._tdt_mode = self._infer_tdt_mode(tdt)
            self._tdt_len = 0
            self._tdt_cum = 0.0

        mode = self._tdt_mode

        done = self._last_done

        if mode == "cumulative_numeric":
            v = self._to_float(tdt[-1])
            if v is not None:
                done = max(done, v)
        elif mode == "durations_numeric":
            for i in range(self._tdt_len, n):
                v = self._to_float(tdt[i])
                if v is not None:
                    self._tdt_cum += max(0.0, v)
            done = max(done, self._tdt_cum)
            self._tdt_len = n
        elif mode == "segments":
            for i in range(self._tdt_len, n):
                seg = tdt[i]
                if isinstance(seg, dict):
                    a = self._to_float(seg.get("start"))
                    b = self._to_float(seg.get("end"))
                    if a is not None and b is not None:
                        self._tdt_cum += max(0.0, b - a)
                    else:
                        d = self._to_float(seg.get("duration"))
                        if d is not None:
                            self._tdt_cum += max(0.0, d)
                elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    a = self._to_float(seg[0])
                    b = self._to_float(seg[1])
                    if a is not None and b is not None:
                        self._tdt_cum += max(0.0, b - a)
            done = max(done, self._tdt_cum)
            self._tdt_len = n
        elif mode == "dict_cumulative":
            last = tdt[-1]
            if isinstance(last, dict):
                for k in ("done", "cumulative", "progress"):
                    v = self._to_float(last.get(k))
                    if v is not None:
                        done = max(done, v)
                        break
        elif mode == "dict_duration":
            for i in range(self._tdt_len, n):
                d = tdt[i]
                if isinstance(d, dict):
                    v = self._to_float(d.get("duration"))
                    if v is not None:
                        self._tdt_cum += max(0.0, v)
            done = max(done, self._tdt_cum)
            self._tdt_len = n
        else:
            # Fallback: try last numeric
            v = self._to_float(tdt[-1])
            if v is not None:
                done = max(done, v)

        if td > 0:
            done = min(done, td)

        self._last_done = max(self._last_done, done)
        return self._last_done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", math.inf) or math.inf)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        done = self._extract_done()
        remaining_work = max(0.0, task_duration - done)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_time = deadline - elapsed

        if self._locked_od:
            return ClusterType.ON_DEMAND

        overhead_to_start_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        guard = max(2.0 * gap, 0.25 * restart_overhead, 1.0)

        if remaining_time <= remaining_work + overhead_to_start_od + guard:
            self._locked_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)