import numbers
from typing import Any, Optional

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

        self._od_committed = False

        self._cached_done = 0.0
        self._cached_task_done_obj_id: Optional[int] = None
        self._cached_task_done_len: Optional[int] = None

    def solve(self, spec_path: str) -> "Solution":
        self._od_committed = False
        self._cached_done = 0.0
        self._cached_task_done_obj_id = None
        self._cached_task_done_len = None
        return self

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, numbers.Real) and not isinstance(x, bool)

    @classmethod
    def _segment_to_seconds(cls, seg: Any) -> float:
        if seg is None:
            return 0.0
        if cls._is_number(seg):
            return float(seg)
        if isinstance(seg, dict):
            if "duration" in seg and cls._is_number(seg["duration"]):
                return float(seg["duration"])
            if "start" in seg and "end" in seg and cls._is_number(seg["start"]) and cls._is_number(seg["end"]):
                return max(0.0, float(seg["end"]) - float(seg["start"]))
            total = 0.0
            for v in seg.values():
                total += cls._segment_to_seconds(v)
            return total
        if isinstance(seg, (tuple, list)):
            if len(seg) == 2 and cls._is_number(seg[0]) and cls._is_number(seg[1]):
                return max(0.0, float(seg[1]) - float(seg[0]))
            total = 0.0
            for v in seg:
                total += cls._segment_to_seconds(v)
            return total
        return 0.0

    def _get_work_done_seconds(self) -> float:
        t = getattr(self, "task_done_time", None)
        if t is None:
            return 0.0

        if self._is_number(t):
            return max(0.0, float(t))

        if isinstance(t, (list, tuple)):
            obj_id = id(t)
            n = len(t)

            if self._cached_task_done_obj_id == obj_id and self._cached_task_done_len is not None:
                if n == self._cached_task_done_len:
                    return self._cached_done
                if n > self._cached_task_done_len:
                    total = self._cached_done
                    for i in range(self._cached_task_done_len, n):
                        total += self._segment_to_seconds(t[i])
                    self._cached_done = total
                    self._cached_task_done_len = n
                    return self._cached_done

            total = 0.0
            for item in t:
                total += self._segment_to_seconds(item)
            self._cached_task_done_obj_id = obj_id
            self._cached_task_done_len = n
            self._cached_done = total
            return self._cached_done

        return max(0.0, self._cached_done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._od_committed = True

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        elapsed = float(getattr(getattr(self, "env", None), "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 0.0) or 0.0)

        work_done = self._get_work_done_seconds()
        if work_done >= task_duration - 1e-9:
            return ClusterType.NONE

        work_remaining = max(0.0, task_duration - work_done)
        time_remaining = max(0.0, deadline - elapsed)

        safety = max(2.0 * gap, 0.5 * restart_overhead, 1.0)

        if self._od_committed:
            return ClusterType.ON_DEMAND

        od_switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        if time_remaining <= work_remaining + od_switch_overhead + safety:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if time_remaining - gap <= work_remaining + restart_overhead + safety:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
