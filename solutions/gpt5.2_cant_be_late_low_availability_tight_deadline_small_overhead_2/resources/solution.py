import json
import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v3"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._inited = False

        self._p_ema = 0.0
        self._p_alpha = 0.12

        self._prev_has_spot: Optional[bool] = None
        self._streak = 0
        self._up_streak = 0
        self._down_streak = 0
        self._mean_up: Optional[float] = None
        self._mean_down: Optional[float] = None
        self._streak_alpha = 0.18

        self._idle_budget: float = 0.0
        self._base_reserve: float = 0.0
        self._min_od_lock: float = 0.0
        self._od_lock_until: float = 0.0

        self._last_work_done: float = 0.0
        self._last_choice: ClusterType = ClusterType.NONE

    def solve(self, spec_path: str) -> "Solution":
        # Optional: read config if present, but keep defaults robust.
        try:
            with open(spec_path, "r") as f:
                cfg = json.load(f)
            # Allow optional overrides if provided.
            pa = cfg.get("p_alpha")
            if isinstance(pa, (int, float)) and 0 < pa < 1:
                self._p_alpha = float(pa)
            sa = cfg.get("streak_alpha")
            if isinstance(sa, (int, float)) and 0 < sa < 1:
                self._streak_alpha = float(sa)
        except Exception:
            pass
        return self

    def _ensure_init(self) -> None:
        if self._inited:
            return
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        slack_total = max(0.0, deadline - task_duration)

        self._base_reserve = max(1800.0, 3.0 * gap, 2.0 * restart_overhead)
        # Keep a meaningful portion of slack for safety; use rest as idle budget.
        reserve_for_finish = max(self._base_reserve, 0.25 * slack_total)
        self._idle_budget = max(0.0, slack_total - reserve_for_finish) * 0.55

        self._min_od_lock = max(600.0, 2.0 * gap, 4.0 * restart_overhead)

        self._last_work_done = self._get_work_done()
        self._inited = True

    def _ema_update(self, prev: Optional[float], new: float, alpha: float) -> float:
        if prev is None:
            return float(new)
        return float(alpha * new + (1.0 - alpha) * prev)

    def _update_availability_stats(self, has_spot: bool) -> None:
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)

        x = 1.0 if has_spot else 0.0
        if self._prev_has_spot is None:
            self._p_ema = x
            self._prev_has_spot = has_spot
            self._streak = 1
        else:
            self._p_ema = self._p_alpha * x + (1.0 - self._p_alpha) * self._p_ema
            if has_spot == self._prev_has_spot:
                self._streak += 1
            else:
                dur = float(self._streak) * gap
                if self._prev_has_spot:
                    self._mean_up = self._ema_update(self._mean_up, dur, self._streak_alpha)
                else:
                    self._mean_down = self._ema_update(self._mean_down, dur, self._streak_alpha)
                self._prev_has_spot = has_spot
                self._streak = 1

        if has_spot:
            self._up_streak = self._streak
            self._down_streak = 0
        else:
            self._down_streak = self._streak
            self._up_streak = 0

    def _get_work_done(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            # Fallback: try common env attributes.
            for name in ("work_done_seconds", "done_seconds", "task_done_seconds", "completed_seconds"):
                v = getattr(self.env, name, None)
                if isinstance(v, (int, float)):
                    return float(v)
            return 0.0

        if isinstance(td, (int, float)):
            return float(td)

        total = 0.0
        if isinstance(td, (list, tuple)):
            for x in td:
                if x is None:
                    continue
                if isinstance(x, (int, float)):
                    total += float(x)
                    continue
                if isinstance(x, (list, tuple)) and len(x) >= 2:
                    try:
                        a = float(x[0])
                        b = float(x[1])
                        total += max(0.0, b - a)
                        continue
                    except Exception:
                        pass
                if isinstance(x, dict):
                    if "duration" in x and isinstance(x["duration"], (int, float)):
                        total += float(x["duration"])
                        continue
                    if "start" in x and "end" in x:
                        try:
                            total += max(0.0, float(x["end"]) - float(x["start"]))
                            continue
                        except Exception:
                            pass
                # Object with duration or start/end attributes
                dur = getattr(x, "duration", None)
                if isinstance(dur, (int, float)):
                    total += float(dur)
                    continue
                start = getattr(x, "start", None)
                end = getattr(x, "end", None)
                if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    total += max(0.0, float(end) - float(start))
                    continue
        return float(total)

    def _get_overhead_remaining(self) -> Optional[float]:
        # Best-effort introspection of env state (if provided by framework).
        candidates = (
            "restart_overhead_remaining",
            "remaining_restart_overhead",
            "restart_time_remaining",
            "remaining_overhead_seconds",
            "overhead_remaining_seconds",
            "pending_restart_overhead",
        )
        for name in candidates:
            v = getattr(self.env, name, None)
            if isinstance(v, (int, float)):
                return float(v)
        return None

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        self._update_availability_stats(has_spot)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        work_done = self._get_work_done()
        self._last_work_done = work_done
        rem_work = max(0.0, task_duration - work_done)

        if rem_work <= 0.0:
            self._last_choice = ClusterType.NONE
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)
        if time_left <= 0.0:
            self._last_choice = ClusterType.NONE
            return ClusterType.NONE

        slack = time_left - rem_work  # how much non-progress time we can afford

        p = min(0.999, max(0.02, float(self._p_ema)))
        risk_add = max(0.0, 0.4 - p) * 7200.0  # up to +2880s when p=0.0
        reserve_idle = self._base_reserve + risk_add
        reserve_switch = self._base_reserve + 0.5 * risk_add

        odonly_threshold = max(2.0 * restart_overhead + gap, 0.2 * self._base_reserve)

        overhead_rem = self._get_overhead_remaining()
        if overhead_rem is not None and overhead_rem > 0.0:
            # Avoid resetting overhead by switching during pending restart.
            if last_cluster_type == ClusterType.ON_DEMAND:
                self._last_choice = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                self._last_choice = ClusterType.SPOT
                return ClusterType.SPOT

        if slack <= odonly_threshold:
            if last_cluster_type == ClusterType.ON_DEMAND:
                self._last_choice = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                self._last_choice = ClusterType.SPOT
                return ClusterType.SPOT
            # If starting from NONE under tight slack, prefer on-demand for stability.
            self._last_choice = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND if not has_spot else ClusterType.ON_DEMAND

        # If we are on on-demand, optionally allow switching to spot only when slack is comfortable.
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                if elapsed < self._od_lock_until:
                    self._last_choice = ClusterType.ON_DEMAND
                    return ClusterType.ON_DEMAND
                if slack <= reserve_switch:
                    self._last_choice = ClusterType.ON_DEMAND
                    return ClusterType.ON_DEMAND
                expected_up = self._mean_up if self._mean_up is not None else (4.0 * gap)
                min_uptime_to_switch = max(3.0 * gap, 4.0 * restart_overhead)
                if expected_up < min_uptime_to_switch and slack <= (reserve_idle + expected_up):
                    self._last_choice = ClusterType.ON_DEMAND
                    return ClusterType.ON_DEMAND
            self._last_choice = ClusterType.SPOT
            return ClusterType.SPOT

        # No spot available: decide NONE (wait) vs ON_DEMAND.
        # If slack is tight, never idle.
        if slack <= reserve_idle:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._od_lock_until = max(self._od_lock_until, elapsed + self._min_od_lock)
            self._last_choice = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # Slack is comfortable: consider idling if we have budget and expect spot to return soon.
        exp_down = self._mean_down if self._mean_down is not None else (2.0 * gap)
        exp_remaining_down = max(gap, exp_down - float(self._down_streak) * gap)

        max_affordable_idle_now = max(0.0, slack - reserve_idle)
        if self._idle_budget >= gap and max_affordable_idle_now >= gap:
            # If we've already been down much longer than expected, stop idling.
            if float(self._down_streak) * gap <= 2.2 * exp_down:
                if exp_remaining_down <= min(self._idle_budget, max_affordable_idle_now):
                    self._idle_budget = max(0.0, self._idle_budget - gap)
                    self._last_choice = ClusterType.NONE
                    return ClusterType.NONE

        if last_cluster_type != ClusterType.ON_DEMAND:
            self._od_lock_until = max(self._od_lock_until, elapsed + self._min_od_lock)
        self._last_choice = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
