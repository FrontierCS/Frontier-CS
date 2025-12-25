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
        self._commit_od = False

        self._spot_ema = 0.65
        self._ema_alpha = 0.06

        self._current_outage_s = 0.0
        self._max_outage_s = 0.0

        self._last_choice: Optional[ClusterType] = None

        self._min_outage_buffer_s = 2.0 * 3600.0
        self._pause_hysteresis_s = 1.0 * 3600.0

    def solve(self, spec_path: str) -> "Solution":
        self._initialized = True
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            if x is None:
                return default
            v = float(x)
            if math.isnan(v) or math.isinf(v):
                return default
            return v
        except Exception:
            return default

    def _work_done_seconds(self) -> float:
        # Best-effort extraction from task_done_time, with multiple possible encodings.
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            for attr in ("task_progress", "progress_seconds", "completed_seconds"):
                if hasattr(self, attr):
                    return max(0.0, self._safe_float(getattr(self, attr), 0.0))
            return 0.0

        if isinstance(tdt, (int, float)):
            return max(0.0, self._safe_float(tdt, 0.0))

        if not isinstance(tdt, (list, tuple)):
            return 0.0

        if len(tdt) == 0:
            return 0.0

        # If looks like monotonic timestamps of cumulative work done.
        try:
            if all(isinstance(x, (int, float)) for x in tdt):
                vals = [self._safe_float(x, 0.0) for x in tdt]
                # If non-decreasing and within plausible bounds, take last as cumulative.
                nondecreasing = all(vals[i] <= vals[i + 1] + 1e-9 for i in range(len(vals) - 1))
                if nondecreasing:
                    last = vals[-1]
                    # Heuristic: if last doesn't exceed task_duration too much, treat as cumulative.
                    td = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
                    if td <= 0 or last <= td * 1.2 + 1e-6:
                        return max(0.0, last)
                # Else treat as per-step segments; sum.
                return max(0.0, sum(max(0.0, v) for v in vals))
        except Exception:
            pass

        done = 0.0
        for seg in tdt:
            if isinstance(seg, (int, float)):
                done += max(0.0, self._safe_float(seg, 0.0))
            elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                a = self._safe_float(seg[0], 0.0)
                b = self._safe_float(seg[1], 0.0)
                if b >= a:
                    done += (b - a)
                else:
                    done += max(0.0, a - b)
        return max(0.0, done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = self._safe_float(getattr(env, "elapsed_seconds", 0.0), 0.0)
        gap = self._safe_float(getattr(env, "gap_seconds", 60.0), 60.0)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        restart_overhead = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        if not self._initialized:
            self._initialized = True
            self._last_choice = last_cluster_type

        # Update spot availability stats
        if has_spot:
            self._current_outage_s = 0.0
        else:
            self._current_outage_s += max(0.0, gap)
            if self._current_outage_s > self._max_outage_s:
                self._max_outage_s = self._current_outage_s

        x = 1.0 if has_spot else 0.0
        self._spot_ema = self._ema_alpha * x + (1.0 - self._ema_alpha) * self._spot_ema
        self._spot_ema = min(0.99, max(0.01, self._spot_ema))

        done = self._work_done_seconds()
        remaining_work = max(0.0, task_duration - done)

        if remaining_work <= 1e-9:
            self._last_choice = ClusterType.NONE
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            self._commit_od = True
            self._last_choice = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work

        min_outage_buf = self._min_outage_buffer_s
        learned_outage_buf = max(min_outage_buf, 1.2 * self._max_outage_s)

        # Extra risk buffer inversely proportional to observed spot availability.
        extra_risk_buf = (1.0 - self._spot_ema) * 3.0 * 3600.0

        risk_buf = learned_outage_buf + extra_risk_buf
        # Account for one likely restart and decision granularity.
        switch_to_od_buf = risk_buf + 2.0 * restart_overhead + 2.0 * gap
        wait_buf = risk_buf + 1.0 * restart_overhead + 2.0 * gap
        must_finish_buf = 1.0 * restart_overhead + 2.0 * gap

        if time_left <= remaining_work + must_finish_buf:
            self._commit_od = True

        if self._commit_od:
            self._last_choice = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        if has_spot:
            if slack <= switch_to_od_buf:
                self._commit_od = True
                self._last_choice = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
            self._last_choice = ClusterType.SPOT
            return ClusterType.SPOT

        # No spot available: either pause or run on-demand based on slack.
        # Add hysteresis to avoid toggling OD <-> NONE.
        if self._last_choice == ClusterType.ON_DEMAND:
            if slack > wait_buf + self._pause_hysteresis_s:
                self._last_choice = ClusterType.NONE
                return ClusterType.NONE
            self._last_choice = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        if slack > wait_buf:
            self._last_choice = ClusterType.NONE
            return ClusterType.NONE

        self._last_choice = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)