import json
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_latest_od"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._od_locked = False
        self._extra_buffer_mult = 1.0
        self._min_extra_buffer_seconds = 0.0

        if args is not None:
            self._extra_buffer_mult = float(getattr(args, "extra_buffer_mult", self._extra_buffer_mult))
            self._min_extra_buffer_seconds = float(
                getattr(args, "min_extra_buffer_seconds", self._min_extra_buffer_seconds)
            )

    def solve(self, spec_path: str) -> "Solution":
        # Optional config from spec_path, if present. Fail-safe.
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = json.load(f)
            if isinstance(spec, dict):
                v = spec.get("extra_buffer_mult", None)
                if v is not None:
                    self._extra_buffer_mult = float(v)
                v = spec.get("min_extra_buffer_seconds", None)
                if v is not None:
                    self._min_extra_buffer_seconds = float(v)
        except Exception:
            pass
        return self

    def _work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            return 0.0
        total = 0.0
        try:
            for x in td:
                if isinstance(x, (int, float)):
                    total += float(x)
                elif isinstance(x, (list, tuple)) and len(x) >= 2:
                    a, b = x[0], x[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        total += float(b) - float(a)
                elif isinstance(x, dict):
                    if "duration" in x and isinstance(x["duration"], (int, float)):
                        total += float(x["duration"])
                    elif "start" in x and "end" in x:
                        a, b = x["start"], x["end"]
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                            total += float(b) - float(a)
        except Exception:
            return 0.0
        if total < 0.0:
            total = 0.0
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0)) if env is not None else 0.0
        gap = float(getattr(env, "gap_seconds", 0.0)) if env is not None else 0.0

        task_duration = float(getattr(self, "task_duration", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        work_done = self._work_done_seconds()
        remaining_work = task_duration - work_done
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Conservative buffer for decision granularity + at least one restart overhead.
        buffer_seconds = self._extra_buffer_mult * (restart_overhead + 2.0 * gap)
        if buffer_seconds < self._min_extra_buffer_seconds:
            buffer_seconds = self._min_extra_buffer_seconds

        latest_safe_od_start = deadline - remaining_work - buffer_seconds

        if self._od_locked:
            return ClusterType.ON_DEMAND

        # If we wait one more step, we'll cross the latest safe start; lock OD now.
        if elapsed + gap >= latest_safe_od_start:
            self._od_locked = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)