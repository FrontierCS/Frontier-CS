import math
from typing import Any, Iterable

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
        self._od_lock = False

    def solve(self, spec_path: str) -> "Solution":
        self._od_lock = False
        return self

    def _work_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0

        try:
            seq = list(tdt)
        except Exception:
            return 0.0

        if not seq:
            return 0.0

        first = seq[0]

        def _is_num(x: Any) -> bool:
            return isinstance(x, (int, float)) and math.isfinite(float(x))

        def _is_pair(x: Any) -> bool:
            return isinstance(x, (tuple, list)) and len(x) == 2 and _is_num(x[0]) and _is_num(x[1])

        if all(_is_num(x) for x in seq):
            vals = [float(x) for x in seq]
            nondecreasing = all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))
            s = float(sum(vals))
            last = float(vals[-1])
            if nondecreasing and s > last * 1.05:
                return max(0.0, last)
            if last > getattr(self, "task_duration", float("inf")) * 1.2 and nondecreasing:
                return max(0.0, min(last, float(getattr(self, "task_duration", last))))
            return max(0.0, min(s, float(getattr(self, "task_duration", s))))
        if all(_is_pair(x) for x in seq):
            total = 0.0
            for a, b in seq:
                a = float(a)
                b = float(b)
                if b > a:
                    total += (b - a)
            return max(0.0, min(total, float(getattr(self, "task_duration", total))))
        if isinstance(first, dict):
            total = 0.0
            for item in seq:
                if not isinstance(item, dict):
                    continue
                if "duration" in item and _is_num(item["duration"]):
                    total += float(item["duration"])
                elif "done" in item and _is_num(item["done"]):
                    total += float(item["done"])
            return max(0.0, min(total, float(getattr(self, "task_duration", total))))
        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 60.0))

        task_duration = float(getattr(self, "task_duration", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        overhead = float(getattr(self, "restart_overhead", 0.0))

        done = self._work_done_seconds()
        remaining = max(0.0, task_duration - done)

        if remaining <= 0.0:
            self._od_lock = False
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # Conservative required time includes a small restart margin.
        margin = max(3.0 * overhead, 0.5 * gap)
        required = remaining + margin
        slack = time_left - required

        panic_buffer = max(gap + 2.0 * overhead, 300.0)
        wait_buffer = panic_buffer
        switch_back_threshold = max(3.0 * wait_buffer, 2.0 * gap + 2.0 * overhead)

        if slack <= panic_buffer:
            self._od_lock = True
            return ClusterType.ON_DEMAND

        if self._od_lock:
            if has_spot and slack >= switch_back_threshold:
                self._od_lock = False
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if slack >= wait_buffer:
            return ClusterType.NONE

        self._od_lock = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)