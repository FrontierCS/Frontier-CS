import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _done_work_seconds(self) -> float:
        env = getattr(self, "env", None)
        if env is not None:
            for attr in ("task_done_seconds", "done_seconds", "completed_seconds", "progress_seconds"):
                if hasattr(env, attr):
                    try:
                        v = float(getattr(env, attr))
                        if math.isfinite(v):
                            return max(0.0, v)
                    except Exception:
                        pass

        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0

        total = 0.0
        try:
            for seg in tdt:
                if seg is None:
                    continue
                if isinstance(seg, (int, float)):
                    total += float(seg)
                    continue
                if isinstance(seg, dict):
                    for k in ("duration", "work", "done", "seconds"):
                        if k in seg:
                            try:
                                total += float(seg[k])
                                break
                            except Exception:
                                pass
                    continue
                if isinstance(seg, (tuple, list)) and seg:
                    x0 = seg[0]
                    if isinstance(x0, (int, float)):
                        total += float(x0)
                    elif len(seg) >= 2 and isinstance(seg[1], (int, float)):
                        total += float(seg[1])
        except Exception:
            return 0.0

        return max(0.0, total)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._done_work_seconds()
        remaining_work = max(0.0, task_duration - done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        od_switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        decision_buffer = gap + restart_overhead

        if remaining_time <= remaining_work + od_switch_overhead + decision_buffer:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
