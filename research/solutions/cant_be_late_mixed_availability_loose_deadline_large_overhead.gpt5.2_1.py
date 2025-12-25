from __future__ import annotations

from typing import Any, Iterable, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_spot_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        self._committed_to_od = False
        return self

    @staticmethod
    def _is_non_decreasing(nums: Iterable[float]) -> bool:
        it = iter(nums)
        try:
            prev = next(it)
        except StopIteration:
            return True
        for x in it:
            if x < prev:
                return False
            prev = x
        return True

    def _work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            return 0.0

        try:
            first = td[0]
        except Exception:
            return 0.0

        # Case 1: list of numbers (durations or cumulative)
        if isinstance(first, (int, float)):
            vals = []
            for x in td:
                if isinstance(x, (int, float)):
                    vals.append(float(x))
                else:
                    break
            if not vals:
                return 0.0
            # If monotonic, treat as cumulative progress (conservative vs sum).
            if len(vals) >= 2 and self._is_non_decreasing(vals):
                return float(vals[-1])
            return float(sum(vals))

        # Case 2: list of (start, end) pairs
        if isinstance(first, (tuple, list)) and len(first) >= 2:
            total = 0.0
            for seg in td:
                if not (isinstance(seg, (tuple, list)) and len(seg) >= 2):
                    continue
                a, b = seg[0], seg[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    if b > a:
                        total += float(b - a)
            return total

        # Case 3: list of dict segments
        if isinstance(first, dict):
            total = 0.0
            for seg in td:
                if not isinstance(seg, dict):
                    continue
                if "duration" in seg and isinstance(seg["duration"], (int, float)):
                    total += float(seg["duration"])
                elif "start" in seg and "end" in seg and isinstance(seg["start"], (int, float)) and isinstance(
                    seg["end"], (int, float)
                ):
                    if seg["end"] > seg["start"]:
                        total += float(seg["end"] - seg["start"])
            return total

        return 0.0

    def _remaining_work_seconds(self) -> float:
        # Prefer any explicit remaining/done attributes if present.
        env = getattr(self, "env", None)
        if env is not None:
            for attr in ("task_remaining_seconds", "remaining_task_seconds", "task_left_seconds"):
                if hasattr(env, attr):
                    v = getattr(env, attr)
                    if isinstance(v, (int, float)):
                        return max(0.0, float(v))
            for attr in ("task_done_seconds", "done_task_seconds", "task_progress_seconds"):
                if hasattr(env, attr):
                    v = getattr(env, attr)
                    if isinstance(v, (int, float)):
                        return max(0.0, float(self.task_duration) - float(v))

        done = self._work_done_seconds()
        return max(0.0, float(self.task_duration) - done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self._remaining_work_seconds()
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        deadline = float(self.deadline)
        remaining_time = deadline - elapsed

        # If we're out of time, try to make progress on on-demand.
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        restart_overhead = float(self.restart_overhead)

        # Conservative switch overhead when starting on-demand from anything else.
        switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Extra margin for discretization / reaction time.
        # Keep modest to preserve score, but non-zero to avoid deadline misses.
        extra_margin = max(600.0, min(2.0 * gap, 1800.0), 0.25 * restart_overhead)

        # If we must run guaranteed capacity to finish, commit to on-demand permanently.
        if remaining_time <= remaining_work + switch_overhead + extra_margin:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)