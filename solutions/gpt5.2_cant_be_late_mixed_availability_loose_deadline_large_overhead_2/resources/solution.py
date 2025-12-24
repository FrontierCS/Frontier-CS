import argparse
from typing import Any, Optional

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
    NAME = "deadline_guard_spot"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self._committed_od = False
        self._buffer_seconds: Optional[float] = None

        self._done_cache = 0.0
        self._done_cache_obj_id = None
        self._done_cache_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _segment_duration(self, seg: Any) -> float:
        if seg is None:
            return 0.0
        if isinstance(seg, (int, float)):
            return float(seg)
        if isinstance(seg, dict):
            if "duration" in seg and isinstance(seg["duration"], (int, float)):
                return float(seg["duration"])
            if "start" in seg and "end" in seg and isinstance(seg["start"], (int, float)) and isinstance(seg["end"], (int, float)):
                return float(seg["end"]) - float(seg["start"])
            if "t0" in seg and "t1" in seg and isinstance(seg["t0"], (int, float)) and isinstance(seg["t1"], (int, float)):
                return float(seg["t1"]) - float(seg["t0"])
            return 0.0
        if isinstance(seg, (tuple, list)) and len(seg) >= 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
            return float(seg[1]) - float(seg[0])
        return 0.0

    def _get_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)

        if not isinstance(td, (list, tuple)):
            return 0.0

        if len(td) == 0:
            self._done_cache = 0.0
            self._done_cache_obj_id = id(td)
            self._done_cache_len = 0
            return 0.0

        # Heuristic: list of cumulative done seconds (monotonic increasing, starts near 0)
        if all(isinstance(x, (int, float)) for x in td):
            last = float(td[-1])
            task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
            if td[0] <= 1e-6 and last >= 0.0 and (task_dur <= 0.0 or last <= task_dur * 1.1):
                monotone = True
                prev = float(td[0])
                for x in td[1:]:
                    fx = float(x)
                    if fx + 1e-6 < prev:
                        monotone = False
                        break
                    prev = fx
                if monotone:
                    # distinguish cumulative vs increments by comparing sum vs last
                    s = float(sum(float(x) for x in td))
                    if s > last * 1.5:
                        return last

        obj_id = id(td)
        if self._done_cache_obj_id == obj_id and self._done_cache_len <= len(td):
            inc = 0.0
            for seg in td[self._done_cache_len :]:
                inc += self._segment_duration(seg)
            self._done_cache += inc
            self._done_cache_len = len(td)
            return self._done_cache

        total = 0.0
        for seg in td:
            total += self._segment_duration(seg)
        self._done_cache = total
        self._done_cache_obj_id = obj_id
        self._done_cache_len = len(td)
        return total

    def _init_buffer(self) -> float:
        if self._buffer_seconds is not None:
            return self._buffer_seconds
        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 0.0) or 0.0)
        r = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Safety margin: cover 1-2 decision steps + overhead uncertainty.
        self._buffer_seconds = max(2.0 * gap, 1.25 * r, 600.0)
        return self._buffer_seconds

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._get_done_seconds()
        remaining = task_duration - done
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND or getattr(env, "cluster_type", None) == ClusterType.ON_DEMAND:
            self._committed_od = True

        buffer_s = self._init_buffer()

        if not self._committed_od:
            od_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
            if time_left <= remaining + od_overhead + buffer_s:
                self._committed_od = True
                return ClusterType.ON_DEMAND

            if has_spot:
                return ClusterType.SPOT
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
