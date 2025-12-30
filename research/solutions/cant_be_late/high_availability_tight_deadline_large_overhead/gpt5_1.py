from typing import Any, Optional, Tuple, Union
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "jit_od_guard"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._committed_to_od = False
        self._safety_margin_steps = 1.0
        self._cached_work_done = 0.0
        self._cached_len = None  # for list-like task_done_time caching
        self._last_seen_task_done_id = None  # fallback if environment uses identity changes

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_safety_margin_seconds(self) -> float:
        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        steps = getattr(self.args, "safety_margin_steps", self._safety_margin_steps)
        try:
            steps = float(steps)
        except Exception:
            steps = self._safety_margin_steps
        return max(0.0, steps * gap)

    def _sum_task_done(self, obj: Any) -> float:
        # Fast paths
        if obj is None:
            return 0.0
        if isinstance(obj, (int, float)):
            return float(obj)
        total = 0.0
        # Common expected structure: list of floats
        if isinstance(obj, (list, tuple)):
            # caching by length if possible
            try:
                current_len = len(obj)
            except Exception:
                current_len = None
            # If it's a list and grew since last read, we can sum incrementally; else recompute
            if current_len is not None:
                if self._cached_len is not None and current_len >= self._cached_len and isinstance(obj, list):
                    # sum only new items if they are numeric; otherwise fall back to full sum
                    try:
                        inc = 0.0
                        for item in obj[self._cached_len:]:
                            if isinstance(item, (int, float)):
                                inc += float(item)
                            elif isinstance(item, dict):
                                if "duration" in item and isinstance(item["duration"], (int, float)):
                                    inc += float(item["duration"])
                                elif "len" in item and isinstance(item["len"], (int, float)):
                                    inc += float(item["len"])
                                elif "seconds" in item and isinstance(item["seconds"], (int, float)):
                                    inc += float(item["seconds"])
                                elif "end" in item and "start" in item and isinstance(item["end"], (int, float)) and isinstance(item["start"], (int, float)):
                                    inc += max(0.0, float(item["end"]) - float(item["start"]))
                            elif isinstance(item, (list, tuple)):
                                if len(item) >= 2 and isinstance(item[0], (int, float)) and isinstance(item[1], (int, float)):
                                    a, b = float(item[0]), float(item[1])
                                    inc += b - a if b >= a else b
                                elif len(item) >= 1 and isinstance(item[0], (int, float)):
                                    inc += float(item[0])
                            # else ignore unrecognized entries
                        self._cached_work_done += inc
                        self._cached_len = current_len
                        return max(0.0, self._cached_work_done)
                    except Exception:
                        pass  # fall back to full recompute
                # full recompute:
                try:
                    for item in obj:
                        if isinstance(item, (int, float)):
                            total += float(item)
                        elif isinstance(item, dict):
                            if "duration" in item and isinstance(item["duration"], (int, float)):
                                total += float(item["duration"])
                            elif "len" in item and isinstance(item["len"], (int, float)):
                                total += float(item["len"])
                            elif "seconds" in item and isinstance(item["seconds"], (int, float)):
                                total += float(item["seconds"])
                            elif "end" in item and "start" in item and isinstance(item["end"], (int, float)) and isinstance(item["start"], (int, float)):
                                total += max(0.0, float(item["end"]) - float(item["start"]))
                        elif isinstance(item, (list, tuple)):
                            if len(item) >= 2 and isinstance(item[0], (int, float)) and isinstance(item[1], (int, float)):
                                a, b = float(item[0]), float(item[1])
                                total += b - a if b >= a else b
                            elif len(item) >= 1 and isinstance(item[0], (int, float)):
                                total += float(item[0])
                    self._cached_len = current_len
                    self._cached_work_done = total
                    return max(0.0, total)
                except Exception:
                    pass  # fall through to generic handling

        if isinstance(obj, dict):
            # try common fields
            for key in ("duration", "dur", "seconds", "work", "done", "total", "sum"):
                v = obj.get(key)
                if isinstance(v, (int, float)):
                    return max(0.0, float(v))
            # try nested start/end
            if "start" in obj and "end" in obj and isinstance(obj["start"], (int, float)) and isinstance(obj["end"], (int, float)):
                return max(0.0, float(obj["end"]) - float(obj["start"]))
            # otherwise try sum of numeric values
            try:
                for v in obj.values():
                    if isinstance(v, (int, float)):
                        total += float(v)
                if total > 0:
                    return total
            except Exception:
                pass

        # As a last resort
        try:
            return max(0.0, float(obj))
        except Exception:
            return 0.0

    def _get_work_done(self) -> float:
        td = getattr(self, "task_done_time", None)
        wd = self._sum_task_done(td)
        try:
            total = float(getattr(self, "task_duration", 0.0) or 0.0)
            if total > 0.0:
                return min(total, wd)
            return wd
        except Exception:
            return wd

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, stay there
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Gather environment values with safe fallbacks
        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        total_task = float(getattr(self, "task_duration", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)

        work_done = self._get_work_done()
        remaining_work = max(0.0, total_task - work_done)

        # If task is done, no need to run
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        # Compute latest safe OD start time
        safety_margin = self._get_safety_margin_seconds()
        latest_safe_start = deadline - (remaining_work + restart_overhead) - safety_margin

        # If we're at or past the latest safe start, switch to OD and stick with it
        if now >= latest_safe_start:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer SPOT if available; else wait (NONE)
        if has_spot:
            return ClusterType.SPOT

        # If SPOT is unavailable and we still have buffer, wait
        # However, if the buffer left is less than one step worth of time, proactively switch to OD
        time_left = deadline - now
        buffer_left = latest_safe_start - now
        if buffer_left <= gap * 0.5:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        try:
            parser.add_argument("--safety_margin_steps", type=float, default=1.0)
        except Exception:
            pass
        args, _ = parser.parse_known_args()
        return cls(args)