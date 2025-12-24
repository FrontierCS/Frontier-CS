import math
from typing import Any, List, Optional, Sequence, Tuple

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_aware_wait_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False
        self._committed_od = False

        self._prev_has_spot: Optional[bool] = None
        self._off_start: Optional[float] = None
        self._off_durations: List[float] = []

        self._total_steps = 0
        self._spot_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        self._initialized = True
        self._committed_od = False

        self._prev_has_spot = None
        self._off_start = None
        self._off_durations = []

        self._total_steps = 0
        self._spot_steps = 0
        return self

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        if x < lo:
            return lo
        if x > hi:
            return hi
        return x

    def _sum_done_work_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            return 0.0

        try:
            first = td[0]
        except Exception:
            return 0.0

        # Common patterns:
        # - list of (start, end)
        # - list of durations
        # - list of dicts with keys like 'start', 'end', 'duration'
        total = 0.0
        try:
            if isinstance(first, (tuple, list)) and len(first) == 2:
                for seg in td:
                    try:
                        a, b = seg
                        total += max(0.0, float(b) - float(a))
                    except Exception:
                        continue
                return total
        except Exception:
            pass

        if isinstance(first, dict):
            for seg in td:
                try:
                    if "duration" in seg:
                        total += max(0.0, float(seg["duration"]))
                    elif "start" in seg and "end" in seg:
                        total += max(0.0, float(seg["end"]) - float(seg["start"]))
                except Exception:
                    continue
            return total

        for x in td:
            try:
                total += max(0.0, float(x))
            except Exception:
                continue
        return total

    def _update_availability_stats(self, has_spot: bool) -> None:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            if not has_spot:
                self._off_start = elapsed
            return

        if self._prev_has_spot and (not has_spot):
            self._off_start = elapsed
        elif (not self._prev_has_spot) and has_spot:
            if self._off_start is not None:
                dur = max(0.0, elapsed - float(self._off_start))
                if dur > 0:
                    self._off_durations.append(dur)
                    if len(self._off_durations) > 2000:
                        self._off_durations = self._off_durations[-1000:]
            self._off_start = None

        self._prev_has_spot = has_spot

    def _expected_remaining_off(self) -> float:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        if self._prev_has_spot is None or self._prev_has_spot:
            return 0.0
        cur_off = 0.0
        if self._off_start is not None:
            cur_off = max(0.0, elapsed - float(self._off_start))

        if self._off_durations:
            avg_off = sum(self._off_durations) / len(self._off_durations)
        else:
            avg_off = 20.0 * 60.0  # default 20 min

        return max(0.0, avg_off - cur_off)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_availability_stats(has_spot)

        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        done_work = self._sum_done_work_seconds()
        remaining_work = max(0.0, task_duration - done_work)
        remaining_time = max(0.0, deadline - elapsed)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        overhead_to_spot = 0.0 if last_cluster_type == ClusterType.SPOT else restart_overhead

        # Conservative buffers for discretization and model mismatch.
        safety = max(2.0 * gap, 0.5 * restart_overhead)

        # Latest safe start for OD to finish on time (conservative by one gap).
        time_needed_od = overhead_to_od + remaining_work + gap + safety
        latest_od_start = deadline - time_needed_od

        # If we've committed to on-demand, never switch back.
        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Hard guard: if near the latest safe start time, commit to OD now.
        if elapsed >= latest_od_start:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # If spot available, generally use it unless we're extremely close to deadline.
        if has_spot:
            # If even a single restart would jeopardize deadline, commit to OD.
            # (This is a bit conservative to protect against a sudden spot loss.)
            if remaining_time <= (remaining_work + restart_overhead + gap + safety):
                self._committed_od = True
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot not available: decide between waiting (NONE) vs switching to OD.
        p = (self._spot_steps / self._total_steps) if self._total_steps > 0 else 0.7
        p = self._clamp(p, 0.05, 0.95)

        # Max time to wait during an outage (higher when spot is historically more available).
        max_wait = 900.0 + 2700.0 * p  # 15 min .. 60+ min

        cur_off = 0.0
        if self._off_start is not None:
            cur_off = max(0.0, elapsed - float(self._off_start))

        expected_rem_off = self._expected_remaining_off()

        # If we can afford to wait expected remaining outage time (plus a step),
        # and we haven't waited too long already, then pause.
        if (cur_off < max_wait) and ((elapsed + expected_rem_off + gap) < (latest_od_start - safety)):
            return ClusterType.NONE

        # Otherwise switch to OD and commit (avoid further restarts & uncertainty).
        self._committed_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
