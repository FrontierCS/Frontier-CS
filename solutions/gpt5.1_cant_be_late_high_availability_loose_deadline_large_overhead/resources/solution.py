import math
from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_progress(self) -> float:
        tdt = getattr(self, "task_done_time", 0.0)
        if isinstance(tdt, (int, float)):
            return float(tdt)
        try:
            items = list(tdt)
        except TypeError:
            return 0.0
        if not items:
            return 0.0
        first = items[0]
        if isinstance(first, (int, float)):
            try:
                return float(sum(items))
            except Exception:
                return 0.0
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            total = 0.0
            for seg in items:
                try:
                    if len(seg) >= 2:
                        start = float(seg[0])
                        end = float(seg[1])
                        if end > start:
                            total += end - start
                except Exception:
                    continue
            return total
        try:
            return float(sum(float(x) for x in items))
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        gap = getattr(self.env, "gap_seconds", 0.0)
        deadline = getattr(self, "deadline", float("inf"))
        task_duration = getattr(self, "task_duration", 0.0)
        restart_overhead = getattr(self, "restart_overhead", 0.0)

        progress = self._compute_progress()
        remaining = max(task_duration - progress, 0.0)
        time_left = deadline - elapsed

        if not math.isfinite(time_left):
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if time_left <= 0:
            return ClusterType.ON_DEMAND

        if gap <= 0:
            safety_margin = restart_overhead
        else:
            safety_margin = 2.0 * gap

        commit_required = remaining + restart_overhead + safety_margin

        if time_left <= commit_required:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
