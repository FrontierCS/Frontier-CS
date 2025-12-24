import math
from typing import Any

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:  # minimal fallback
        def __init__(self, *args, **kwargs):
            self.env = type("Env", (), {"elapsed_seconds": 0.0, "gap_seconds": 60.0, "cluster_type": ClusterType.NONE})()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._args = args
        self._safety_steps = 1

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)
        total = 0.0
        try:
            for seg in td:
                if seg is None:
                    continue
                if isinstance(seg, (int, float)):
                    total += float(seg)
                elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    a, b = seg[0], seg[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        total += float(b) - float(a)
                elif isinstance(seg, dict):
                    if "duration" in seg and isinstance(seg["duration"], (int, float)):
                        total += float(seg["duration"])
                    elif "start" in seg and "end" in seg:
                        a, b = seg["start"], seg["end"]
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                            total += float(b) - float(a)
        except Exception:
            return 0.0
        return max(0.0, total)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._work_done_seconds()
        remaining_work = task_duration - done
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 1e-9:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        safety = max(0.0, gap) * float(self._safety_steps)
        need_if_od_now = remaining_work + restart_overhead
        if need_if_od_now + safety >= remaining_time:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
