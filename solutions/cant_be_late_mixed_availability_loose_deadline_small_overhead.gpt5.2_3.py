from __future__ import annotations

import json
import os
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_deadline_guard_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._initialized = False

        self._p_ema = 0.5
        self._toggle_ema = 0.1
        self._last_has_spot: Optional[bool] = None
        self._consec_spot_avail = 0
        self._consec_spot_unavail = 0

        self._mode_commit_od = False
        self._od_cooldown_until = 0.0

        self._last_work_done = 0.0
        self._spec_overrides: dict[str, Any] = {}

    def solve(self, spec_path: str) -> "Solution":
        try:
            if spec_path and os.path.exists(spec_path):
                with open(spec_path, "r") as f:
                    txt = f.read().strip()
                if txt:
                    if txt[0] in "{[":
                        self._spec_overrides = json.loads(txt)
                    else:
                        self._spec_overrides = {}
        except Exception:
            self._spec_overrides = {}
        return self

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        try:
            self._od_cooldown_until = float(getattr(self.env, "elapsed_seconds", 0.0))
        except Exception:
            self._od_cooldown_until = 0.0

    def _calc_work_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return self._last_work_done

        try:
            if isinstance(tdt, (int, float)):
                return float(tdt)

            if isinstance(tdt, (list, tuple)):
                if not tdt:
                    return 0.0
                last = tdt[-1]
                if isinstance(last, (int, float)):
                    val = float(last)
                    if 0.0 <= val <= float(getattr(self, "task_duration", val) or val) + 1e-6:
                        return val
                    # If it's likely timestamps rather than progress, fall back to summing segments below.

                total = 0.0
                for seg in tdt:
                    if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                        a, b = seg[0], seg[1]
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                            if b >= a:
                                total += float(b - a)
                    elif isinstance(seg, dict):
                        a = seg.get("start")
                        b = seg.get("end")
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b >= a:
                            total += float(b - a)
                if total > 0.0:
                    return total

                # Fallback: if list looks like monotonically increasing progress samples
                nums = [x for x in tdt if isinstance(x, (int, float))]
                if nums:
                    return float(max(nums))
        except Exception:
            pass

        return self._last_work_done

    def _od_cooldown_duration(self, gap: float, overhead: float) -> float:
        # Minimum duration to stay on OD once started to avoid thrashing.
        dur = max(1800.0, 6.0 * gap, 10.0 * overhead)  # ~30min or larger
        dur += min(3600.0, max(0.0, self._toggle_ema) * 7200.0)  # add up to 1h when highly intermittent
        return min(dur, 3.0 * 3600.0)

    def _dynamic_buffer(self, time_left: float, gap: float, overhead: float) -> float:
        # Keep a reserve slack to account for restart overhead and intermittent spot.
        base = 3600.0  # 1 hour base buffer
        steps_per_hour = 3600.0 / max(gap, 1.0)
        toggles_per_hour = max(0.0, self._toggle_ema) * steps_per_hour
        horizon_h = min(4.0, max(0.0, time_left) / 3600.0)
        expected_overhead = horizon_h * toggles_per_hour * overhead * 0.7
        buf = base + 2.0 * overhead + 2.0 * gap + expected_overhead
        return min(max(buf, 0.0), 6.0 * 3600.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        # Update spot availability statistics.
        if self._last_has_spot is None:
            self._p_ema = 1.0 if has_spot else 0.0
        else:
            alpha = 0.02
            self._p_ema = (1.0 - alpha) * self._p_ema + alpha * (1.0 if has_spot else 0.0)

            toggled = 1.0 if (has_spot != self._last_has_spot) else 0.0
            beta = 0.05
            self._toggle_ema = (1.0 - beta) * self._toggle_ema + beta * toggled

        if has_spot:
            self._consec_spot_avail += 1
            self._consec_spot_unavail = 0
        else:
            self._consec_spot_unavail += 1
            self._consec_spot_avail = 0

        self._last_has_spot = has_spot

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 300.0))
        overhead = float(getattr(self, "restart_overhead", 0.0))

        work_done = self._calc_work_done()
        if work_done < self._last_work_done:
            work_done = self._last_work_done
        self._last_work_done = work_done

        task_duration = float(getattr(self, "task_duration", 0.0))
        remaining_work = max(0.0, task_duration - work_done)

        deadline = float(getattr(self, "deadline", 0.0))
        time_left = max(0.0, deadline - elapsed)

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        if time_left <= 1e-9:
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work
        buffer = self._dynamic_buffer(time_left=time_left, gap=gap, overhead=overhead)

        # Hard commit to OD if we are close to deadline.
        required_rate = remaining_work / max(time_left, 1e-9)
        if (not self._mode_commit_od) and (time_left <= remaining_work + buffer or required_rate >= 0.97):
            self._mode_commit_od = True

        if self._mode_commit_od:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._od_cooldown_until = elapsed + self._od_cooldown_duration(gap, overhead)
            return ClusterType.ON_DEMAND

        # Dynamic anti-thrashing parameters.
        k_up = 1
        if self._toggle_ema > 0.18:
            k_up += 1
        if self._p_ema < 0.45:
            k_up += 1
        k_up = min(max(k_up, 1), 3)

        wait_cap_steps = int(2 + 10.0 * max(0.0, min(1.0, self._p_ema)) - 6.0 * max(0.0, min(1.0, self._toggle_ema)))
        wait_cap_steps = min(max(wait_cap_steps, 1), 12)

        # Decision.
        if has_spot:
            # If currently on OD, only switch to spot if spot looks stable enough and we have slack.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if elapsed < self._od_cooldown_until:
                    return ClusterType.ON_DEMAND
                if self._consec_spot_avail < k_up:
                    return ClusterType.ON_DEMAND
                if slack <= buffer + 1800.0:
                    return ClusterType.ON_DEMAND
                if remaining_work <= 7200.0 and slack <= 7200.0:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT
            return ClusterType.SPOT

        # No spot available
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        spare = slack - buffer
        if spare <= 0.0:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._od_cooldown_until = elapsed + self._od_cooldown_duration(gap, overhead)
            return ClusterType.ON_DEMAND

        max_wait_steps = int(spare / max(gap, 1.0))
        max_wait_steps = min(max_wait_steps, wait_cap_steps)

        if max_wait_steps <= 0:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._od_cooldown_until = elapsed + self._od_cooldown_duration(gap, overhead)
            return ClusterType.ON_DEMAND

        if self._consec_spot_unavail <= max_wait_steps:
            return ClusterType.NONE

        if last_cluster_type != ClusterType.ON_DEMAND:
            self._od_cooldown_until = elapsed + self._od_cooldown_duration(gap, overhead)
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
