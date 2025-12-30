from __future__ import annotations

from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_deadline_guard_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._lock_on_demand = False

        self._cached_done_len = 0
        self._cached_done_sum = 0.0
        self._cached_done_is_cumulative_numeric = False
        self._cached_done_max = 0.0
        self._cached_done_checked_type = False

        self._spot_seen = 0
        self._spot_avail = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _segment_duration_seconds(self, seg: Any) -> float:
        try:
            if isinstance(seg, (int, float)):
                return float(seg)
            if isinstance(seg, dict):
                if "duration" in seg and isinstance(seg["duration"], (int, float)):
                    return float(seg["duration"])
                if "start" in seg and "end" in seg and isinstance(seg["start"], (int, float)) and isinstance(seg["end"], (int, float)):
                    return float(seg["end"]) - float(seg["start"])
                if "begin" in seg and "finish" in seg and isinstance(seg["begin"], (int, float)) and isinstance(seg["finish"], (int, float)):
                    return float(seg["finish"]) - float(seg["begin"])
                return 0.0
            if isinstance(seg, (tuple, list)):
                if len(seg) == 0:
                    return 0.0
                if len(seg) == 1:
                    return float(seg[0]) if isinstance(seg[0], (int, float)) else 0.0
                a, b = seg[0], seg[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    # Prefer interpreting as (start, end) if it looks like that.
                    if b >= a:
                        return float(b) - float(a)
                    return float(a)
                if isinstance(a, (int, float)) and not isinstance(b, (int, float)):
                    return float(a)
                return 0.0

            if hasattr(seg, "duration"):
                d = getattr(seg, "duration")
                if isinstance(d, (int, float)):
                    return float(d)
            if hasattr(seg, "start") and hasattr(seg, "end"):
                s = getattr(seg, "start")
                e = getattr(seg, "end")
                if isinstance(s, (int, float)) and isinstance(e, (int, float)):
                    return float(e) - float(s)
        except Exception:
            return 0.0
        return 0.0

    def _get_work_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, list) or not tdt:
            return 0.0

        # Determine representation once:
        if not self._cached_done_checked_type:
            self._cached_done_checked_type = True
            all_numeric = True
            nondecreasing = True
            prev = None
            mx = float("-inf")
            for x in tdt:
                if not isinstance(x, (int, float)):
                    all_numeric = False
                    break
                fx = float(x)
                if prev is not None and fx < prev:
                    nondecreasing = False
                prev = fx
                if fx > mx:
                    mx = fx
            if all_numeric and nondecreasing:
                # Heuristic: if list is cumulative progress checkpoints, max should be near task_duration.
                # If list is per-step durations, sum should be near task_duration.
                s = float(sum(float(x) for x in tdt))
                self._cached_done_max = mx if mx != float("-inf") else 0.0
                td = float(getattr(self, "task_duration", 0.0) or 0.0)
                if td > 0 and s > td * 1.2 and self._cached_done_max <= td * 1.2:
                    self._cached_done_is_cumulative_numeric = True
                    self._cached_done_sum = self._cached_done_max
                    self._cached_done_len = len(tdt)
                    return self._cached_done_sum

        if self._cached_done_is_cumulative_numeric:
            # Just take max; update if new items appended.
            if len(tdt) != self._cached_done_len:
                mx = self._cached_done_max
                for i in range(self._cached_done_len, len(tdt)):
                    x = tdt[i]
                    if isinstance(x, (int, float)):
                        fx = float(x)
                        if fx > mx:
                            mx = fx
                self._cached_done_max = mx
                self._cached_done_sum = mx
                self._cached_done_len = len(tdt)
            return self._cached_done_sum

        # Default: sum durations/segments, incrementally.
        if len(tdt) != self._cached_done_len:
            acc = self._cached_done_sum
            for i in range(self._cached_done_len, len(tdt)):
                acc += self._segment_duration_seconds(tdt[i])
            self._cached_done_sum = acc
            self._cached_done_len = len(tdt)
        return self._cached_done_sum

    def _buffer_seconds(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        base = max(2.0 * gap, 3.0 * oh, gap + oh)

        p = (self._spot_avail + 1.0) / (self._spot_seen + 2.0)
        extra = 0.0
        if p < 0.6:
            extra = ((0.6 - p) / 0.6) * (3.0 * gap)  # up to +3 gaps
        return base + extra

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._spot_seen += 1
        if has_spot:
            self._spot_avail += 1

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        work_done = self._get_work_done_seconds()
        remaining_work = max(0.0, task_duration - work_done)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_time = deadline - elapsed

        # If we're already in the "must finish" phase, never leave on-demand.
        if self._lock_on_demand:
            return ClusterType.ON_DEMAND

        # If spot is available, prefer spot unless we are already on on-demand and too close to switch safely.
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
                buf = self._buffer_seconds()
                # Only switch if still comfortably feasible accounting for a restart penalty.
                if remaining_time >= remaining_work + oh + buf:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available.
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        # Decide whether to wait (NONE) or start on-demand now.
        # If we wait this step, can we still finish by switching to on-demand immediately after?
        oh_next = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        buf = self._buffer_seconds()
        remaining_time_after_wait = remaining_time - gap

        if remaining_time_after_wait >= remaining_work + oh_next + buf:
            return ClusterType.NONE

        self._lock_on_demand = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)