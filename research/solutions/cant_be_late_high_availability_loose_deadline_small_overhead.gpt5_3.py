from typing import Any, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except Exception:
            pass
        self._od_lock: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _progress_seconds(self) -> float:
        try:
            tdt = getattr(self, "task_done_time", [])
            if isinstance(tdt, (list, tuple)):
                return float(sum(tdt))
            try:
                return float(tdt)
            except Exception:
                return 0.0
        except Exception:
            return 0.0

    def _safety_margins(self) -> Tuple[float, float]:
        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        base_margin = max(1800.0, 2.0 * gap, 3.0 * overhead)
        exit_extra = max(600.0, 2.0 * gap, overhead)
        return base_margin, base_margin + exit_extra

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = self._progress_seconds()
        task_duration = getattr(self, "task_duration", 0.0) or 0.0
        remain = max(task_duration - done, 0.0)
        if remain <= 1e-9:
            self._od_lock = False
            return ClusterType.NONE

        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        deadline = getattr(self, "deadline", float("inf")) or float("inf")
        time_left = max(deadline - elapsed, 0.0)

        overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        margin, exit_margin = self._safety_margins()

        # Commit to OD if we are at or past the latest safe start time for OD
        if time_left <= remain + overhead + margin:
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # If locked into OD, potentially unlock if we have ample slack and spot is available
        if self._od_lock:
            if has_spot and time_left > remain + overhead + exit_margin:
                self._od_lock = False
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Not locked and not at commit threshold: prefer spot, otherwise wait
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)