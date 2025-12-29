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
        self.args = args
        self._committed_to_od = False
        self._safety_seconds: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _completed_work_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)
        if not isinstance(tdt, (list, tuple)):
            return 0.0

        total = 0.0
        for seg in tdt:
            if seg is None:
                continue
            if isinstance(seg, (int, float)):
                total += float(seg)
                continue
            if isinstance(seg, (list, tuple)) and seg:
                if len(seg) >= 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                    a = float(seg[0])
                    b = float(seg[1])
                    total += (b - a) if b >= a else b
                elif len(seg) == 1 and isinstance(seg[0], (int, float)):
                    total += float(seg[0])
        return max(0.0, total)

    def _ensure_safety_seconds(self) -> float:
        if self._safety_seconds is not None:
            return self._safety_seconds

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Conservative buffer for discrete timesteps + one restart.
        self._safety_seconds = overhead + 2.0 * gap + 1.0
        return self._safety_seconds

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not has_spot and last_cluster_type == ClusterType.SPOT:
            # Never request spot when unavailable (required by spec).
            pass

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", getattr(self, "deadline", 0.0)) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)

        completed = self._completed_work_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(0.0, task_duration - completed)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        safety = self._ensure_safety_seconds()
        commit_time = deadline - remaining_work - safety

        if elapsed >= commit_time:
            self._committed_to_od = True
        else:
            # If we're within one decision step of the commit boundary and spot is unavailable,
            # start on-demand now to avoid losing an entire timestep.
            if (elapsed + gap) >= commit_time and not has_spot:
                self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)