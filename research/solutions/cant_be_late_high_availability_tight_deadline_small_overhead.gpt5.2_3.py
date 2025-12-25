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

        self._initialized = False

        self._ewma_spot = 0.65
        self._alpha = 0.05

        self._spot_streak = 0
        self._no_spot_streak = 0

        self._on_od = False
        self._od_committed = False
        self._od_start_ts = 0.0

        self._pending_overhead = 0.0

        self._done_len = 0
        self._done_sum = 0.0

        self._min_od_run = 15 * 60.0
        self._min_work_to_switch_back = 2 * 3600.0
        self._p_switch_back = 0.55

        self._guard = 0.0
        self._commit_slack = 0.0
        self._back_slack = 0.0
        self._spot_streak_needed = 2

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _entry_duration(entry: Any) -> float:
        try:
            if isinstance(entry, (int, float)):
                if math.isfinite(entry) and entry > 0:
                    return float(entry)
                return 0.0
            if isinstance(entry, (tuple, list)) and len(entry) == 2:
                a, b = entry
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    if math.isfinite(a) and math.isfinite(b):
                        d = float(b) - float(a)
                        return d if d > 0 else 0.0
                return 0.0
            if isinstance(entry, dict):
                if "duration" in entry and isinstance(entry["duration"], (int, float)):
                    d = float(entry["duration"])
                    return d if math.isfinite(d) and d > 0 else 0.0
                if "start" in entry and "end" in entry:
                    a = entry["start"]
                    b = entry["end"]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        if math.isfinite(a) and math.isfinite(b):
                            d = float(b) - float(a)
                            return d if d > 0 else 0.0
                return 0.0
        except Exception:
            return 0.0
        return 0.0

    def _work_done(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if not isinstance(lst, list) or not lst:
            self._done_len = 0
            self._done_sum = 0.0
            return 0.0

        n = len(lst)
        if n < self._done_len:
            self._done_len = 0
            self._done_sum = 0.0

        for i in range(self._done_len, n):
            self._done_sum += self._entry_duration(lst[i])

        self._done_len = n
        return self._done_sum

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        self._guard = max(gap, 0.25 * overhead)
        self._commit_slack = 3.0 * overhead + 2.0 * gap
        self._back_slack = 2.0 * overhead + 2.0 * gap

        if gap > 0:
            self._spot_streak_needed = max(2, int(math.ceil(overhead / gap)))
        else:
            self._spot_streak_needed = 2

        self._initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Update streaks and EWMA
        if has_spot:
            self._spot_streak += 1
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1
            self._spot_streak = 0

        x = 1.0 if has_spot else 0.0
        self._ewma_spot = (1.0 - self._alpha) * self._ewma_spot + self._alpha * x

        # Decrement pending overhead for the cluster we used last step
        if last_cluster_type in (ClusterType.SPOT, ClusterType.ON_DEMAND) and gap > 0:
            self._pending_overhead = max(0.0, self._pending_overhead - gap)
        else:
            self._pending_overhead = 0.0

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        work_done = self._work_done()
        remaining_work = max(0.0, task_duration - work_done)
        remaining_time = max(0.0, deadline - elapsed)

        if remaining_work <= 0.0:
            self._on_od = False
            self._od_committed = False
            self._pending_overhead = 0.0
            return ClusterType.NONE

        slack = remaining_time - remaining_work

        # Avoid switching during overhead if possible (prevents overhead reset thrash)
        if self._pending_overhead > 0.0:
            if last_cluster_type == ClusterType.ON_DEMAND:
                self._on_od = True
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                self._on_od = False
                return ClusterType.SPOT
            # If spot not available, we must choose OD or NONE; fall through.

        # Commit to OD when slack is tight (prevents multiple restarts from causing deadline miss)
        if not self._od_committed and slack <= self._commit_slack:
            self._od_committed = True

        if self._od_committed:
            self._on_od = True
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._pending_overhead = overhead
            return ClusterType.ON_DEMAND

        # If currently on OD, consider switching back to SPOT with hysteresis
        if self._on_od:
            if has_spot:
                od_age = elapsed - self._od_start_ts
                if (
                    od_age >= self._min_od_run
                    and self._spot_streak >= self._spot_streak_needed
                    and slack >= self._back_slack
                    and remaining_work >= self._min_work_to_switch_back
                    and self._ewma_spot >= self._p_switch_back
                ):
                    self._on_od = False
                    if last_cluster_type != ClusterType.SPOT:
                        self._pending_overhead = overhead
                    return ClusterType.SPOT

            self._on_od = True
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._pending_overhead = overhead
            return ClusterType.ON_DEMAND

        # Not on OD: prefer SPOT when available
        if has_spot:
            self._on_od = False
            if last_cluster_type != ClusterType.SPOT:
                self._pending_overhead = overhead
            return ClusterType.SPOT

        # SPOT unavailable: decide between waiting (NONE) and switching to OD
        # Wait only if it is still feasible to finish by deadline even if we go OD next step and spot never returns.
        # If we wait, we'd likely need to start OD from NONE, incurring overhead.
        can_wait = (remaining_time - gap) >= (remaining_work + overhead + self._guard)

        if can_wait:
            self._on_od = False
            self._pending_overhead = 0.0
            return ClusterType.NONE

        self._on_od = True
        self._od_start_ts = elapsed
        self._pending_overhead = overhead
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)