from typing import Any, List, Tuple, Dict, Optional
import math

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_backup_min_cost"

    def __init__(self, args=None):
        super().__init__(args)
        self._lock_to_on_demand: bool = False
        self._od_hold_until: float = -1.0
        self._progress_cache_key: Optional[Tuple[int, int]] = None
        self._progress_cache_value: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _safe_float(self, v: Any, default: float = 0.0) -> float:
        try:
            return float(v)
        except Exception:
            return default

    def _sum_segment_list(self, segs: List[Any]) -> float:
        # Sum durations from a list of numeric durations
        total = 0.0
        for x in segs:
            try:
                total += float(x)
            except Exception:
                pass
        return total

    def _sum_tuple_segments(self, segs: List[Tuple[Any, Any]]) -> float:
        total = 0.0
        for s in segs:
            try:
                a = float(s[0])
                b = float(s[1])
                if b > a:
                    total += (b - a)
            except Exception:
                continue
        return total

    def _sum_dict_segments(self, segs: List[Dict[str, Any]]) -> float:
        total = 0.0
        for s in segs:
            if not isinstance(s, dict):
                continue
            if 'duration' in s:
                try:
                    total += float(s['duration'])
                    continue
                except Exception:
                    pass
            a = None
            b = None
            for key in ('start', 't_start', 'begin', 's'):
                if key in s:
                    try:
                        a = float(s[key])
                        break
                    except Exception:
                        a = None
            for key in ('end', 't_end', 'finish', 'e'):
                if key in s:
                    try:
                        b = float(s[key])
                        break
                    except Exception:
                        b = None
            if a is not None and b is not None and b > a:
                total += (b - a)
        return total

    def _get_progress_done_seconds(self) -> float:
        # Tries to robustly interpret task_done_time across various possible formats.
        # Cache based on (id(list), len(list))
        segs = getattr(self, 'task_done_time', None)
        if not isinstance(segs, (list, tuple)):
            # Fallback to possible env attributes
            for name in ('work_done', 'work_done_seconds', 'done_seconds', 'task_done',
                         'progress_seconds', 'progress', 'total_done_seconds'):
                if hasattr(self.env, name):
                    val = getattr(self.env, name)
                    if isinstance(val, (int, float)):
                        return float(val)
            return 0.0

        key = (id(segs), len(segs))
        if self._progress_cache_key == key:
            return min(self._progress_cache_value, float(self.task_duration))

        total = 0.0
        if len(segs) == 0:
            total = 0.0
        else:
            first = segs[0]
            if isinstance(first, dict):
                total = self._sum_dict_segments(segs)  # type: ignore
            elif isinstance(first, (list, tuple)) and len(first) >= 2:
                total = self._sum_tuple_segments(segs)  # type: ignore
            elif isinstance(first, (int, float)):
                # Could be a list of durations or a list of cumulative values/timestamps.
                ssum = self._sum_segment_list(segs)  # sum of numerics
                if ssum <= float(self.task_duration) * 1.1:
                    total = ssum
                else:
                    # Treat as cumulative: use the max/last numeric <= task_duration
                    last_val = 0.0
                    try:
                        last_val = float(segs[-1])
                    except Exception:
                        # fallback: use maximum
                        try:
                            last_val = max(float(x) for x in segs if isinstance(x, (int, float)))
                        except Exception:
                            last_val = 0.0
                    total = last_val if last_val <= float(self.task_duration) * 1.1 else 0.0
            else:
                # Unknown format; fallback to recomputing from potential env fields
                for name in ('work_done', 'work_done_seconds', 'done_seconds', 'task_done',
                             'progress_seconds', 'progress', 'total_done_seconds'):
                    if hasattr(self.env, name):
                        val = getattr(self.env, name)
                        if isinstance(val, (int, float)):
                            total = float(val)
                            break

        self._progress_cache_key = key
        self._progress_cache_value = float(total)
        return min(float(total), float(self.task_duration))

    def _safety_fudge_seconds(self) -> float:
        # Add a small buffer to handle step discretization and unexpected small delays
        step = self._safe_float(getattr(self.env, 'gap_seconds', 60.0), 60.0)
        overhead = self._safe_float(getattr(self, 'restart_overhead', 0.0), 0.0)
        # 1 step + 10% of overhead as fudge
        return step + 0.1 * overhead

    def _idle_wait_buffer(self) -> float:
        # Minimum idle wait buffer to decide whether to pause (NONE) when spot is unavailable.
        step = self._safe_float(getattr(self.env, 'gap_seconds', 60.0), 60.0)
        overhead = self._safe_float(getattr(self, 'restart_overhead', 0.0), 0.0)
        # Require ability to wait at least max(2 steps, 0.5 * overhead)
        return max(2.0 * step, 0.5 * overhead)

    def _set_od_hold(self):
        # Hold ON_DEMAND for at least a small window to avoid thrashing
        step = self._safe_float(getattr(self.env, 'gap_seconds', 60.0), 60.0)
        overhead = self._safe_float(getattr(self, 'restart_overhead', 0.0), 0.0)
        hold = max(2.0 * step, 0.5 * overhead)
        now = self._safe_float(getattr(self.env, 'elapsed_seconds', 0.0), 0.0)
        self._od_hold_until = now + hold

    def _should_lock_on_demand(self, remaining: float, time_left: float) -> bool:
        overhead = self._safe_float(getattr(self, 'restart_overhead', 0.0), 0.0)
        fudge = self._safety_fudge_seconds()
        # Lock when only enough time remains to run purely on OD including one restart overhead
        return time_left <= (remaining + overhead + fudge)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Compute remaining work and time to deadline
        done = self._get_progress_done_seconds()
        total = self._safe_float(getattr(self, 'task_duration', 0.0), 0.0)
        remaining = max(0.0, total - done)

        if remaining <= 0.0:
            # Already finished
            return ClusterType.NONE

        now = self._safe_float(getattr(self.env, 'elapsed_seconds', 0.0), 0.0)
        deadline = self._safe_float(getattr(self, 'deadline', getattr(self.env, 'deadline', 0.0)), 0.0)
        time_left = deadline - now
        if time_left <= 0.0:
            # Out of time; choose OD to maximize completion (failsafe)
            self._lock_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Determine lock to ON_DEMAND if near deadline
        if not self._lock_to_on_demand and self._should_lock_on_demand(remaining, time_left):
            self._lock_to_on_demand = True

        # If locked, always use ON_DEMAND to guarantee completion
        if self._lock_to_on_demand:
            return ClusterType.ON_DEMAND

        # If we are within an OD hold window to avoid thrashing, keep OD
        if now < self._od_hold_until:
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available and not locked
        if has_spot:
            return ClusterType.SPOT

        # Spot not available; decide between waiting (NONE) or using ON_DEMAND
        # Compute idle budget before we must start OD to still finish
        overhead = self._safe_float(getattr(self, 'restart_overhead', 0.0), 0.0)
        fudge = self._safety_fudge_seconds()
        idle_budget = time_left - (remaining + overhead + fudge)

        if idle_budget >= self._idle_wait_buffer():
            # Enough slack to wait for spot to return
            return ClusterType.NONE

        # Not enough slack: use ON_DEMAND and hold briefly to avoid immediate thrash
        self._set_od_hold()
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)