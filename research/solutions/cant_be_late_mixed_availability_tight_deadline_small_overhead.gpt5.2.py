from __future__ import annotations

import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_spot_od_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._inited = False
        self._gap = 60.0

        self._last_elapsed = -1.0

        self._prev_has_spot: Optional[bool] = None
        self._n_steps = 0
        self._n_avail = 0
        self._n_trans_on = 0
        self._n_trans_off = 0

        self._on_streak_steps = 0
        self._off_streak_steps = 0

        self._ema_on_seconds = 3600.0
        self._ema_off_seconds = 600.0
        self._ema_alpha = 0.12

        self._urgency = 0  # 0=prefer spot/wait, 1=hybrid, 2=od_only
        self._od_lock_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _wilson_lower(k: float, n: float, z: float = 1.64) -> float:
        if n <= 0:
            return 0.0
        phat = k / n
        denom = 1.0 + (z * z) / n
        center = phat + (z * z) / (2.0 * n)
        adj = z * math.sqrt(max(0.0, (phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n))
        low = (center - adj) / denom
        if low < 0.0:
            return 0.0
        if low > 1.0:
            return 1.0
        return low

    def _reset_episode_state(self):
        self._prev_has_spot = None
        self._n_steps = 0
        self._n_avail = 0
        self._n_trans_on = 0
        self._n_trans_off = 0
        self._on_streak_steps = 0
        self._off_streak_steps = 0
        self._ema_on_seconds = 3600.0
        self._ema_off_seconds = 600.0
        self._urgency = 0
        self._od_lock_steps = 0

    def _maybe_init_or_reset(self):
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        if not self._inited:
            self._gap = float(getattr(self.env, "gap_seconds", 60.0)) or 60.0
            self._inited = True
            self._last_elapsed = elapsed
            if elapsed <= 0.0:
                self._reset_episode_state()
            return

        if elapsed + 1e-9 < self._last_elapsed or elapsed <= 0.0 and self._last_elapsed > 0.0:
            self._reset_episode_state()

        self._last_elapsed = elapsed
        self._gap = float(getattr(self.env, "gap_seconds", self._gap)) or self._gap

    def _update_trace_stats(self, has_spot: bool):
        self._n_steps += 1
        if has_spot:
            self._n_avail += 1

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            if has_spot:
                self._on_streak_steps = 1
                self._off_streak_steps = 0
            else:
                self._off_streak_steps = 1
                self._on_streak_steps = 0
            return

        prev = self._prev_has_spot
        if has_spot:
            if prev:
                self._on_streak_steps += 1
            else:
                self._n_trans_on += 1
                off_len_sec = self._off_streak_steps * self._gap
                self._ema_off_seconds = (1.0 - self._ema_alpha) * self._ema_off_seconds + self._ema_alpha * max(
                    self._gap, off_len_sec
                )
                self._on_streak_steps = 1
                self._off_streak_steps = 0
        else:
            if prev:
                self._n_trans_off += 1
                on_len_sec = self._on_streak_steps * self._gap
                self._ema_on_seconds = (1.0 - self._ema_alpha) * self._ema_on_seconds + self._ema_alpha * max(
                    self._gap, on_len_sec
                )
                self._off_streak_steps = 1
                self._on_streak_steps = 0
            else:
                self._off_streak_steps += 1

        self._prev_has_spot = has_spot

    def _work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)
        try:
            s = 0.0
            for x in td:
                try:
                    s += float(x)
                except Exception:
                    continue
            return s
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_init_or_reset()
        self._update_trace_stats(bool(has_spot))

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = self._gap
        deadline = float(getattr(self, "deadline", getattr(self, "deadline_seconds", getattr(self, "deadline", 0.0))) or 0.0)
        if deadline <= 0.0:
            deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        if deadline <= 0.0:
            deadline = float(getattr(self, "deadline_seconds", 0.0) or 0.0)
        if deadline <= 0.0:
            deadline = float(getattr(self, "deadline", 0.0) or 0.0)

        remaining_time = max(0.0, float(getattr(self, "deadline", 0.0) or deadline) - elapsed)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        work_done = self._work_done_seconds()
        remaining_work = max(0.0, task_duration - work_done)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        slack = remaining_time - remaining_work
        if remaining_time <= 1e-6:
            return ClusterType.ON_DEMAND

        required_speed = remaining_work / remaining_time

        safety = 12.0 * 60.0
        panic_slack = max(45.0 * 60.0, 8.0 * restart_overhead, 3.0 * gap)
        must_run_continuously = remaining_time <= remaining_work + restart_overhead + safety or required_speed >= 0.985

        if must_run_continuously or slack <= panic_slack:
            self._urgency = 2
        else:
            n0 = 40.0
            p0 = 0.5
            k_adj = self._n_avail + p0 * n0
            n_adj = self._n_steps + n0
            p_low = self._wilson_lower(k_adj, n_adj, z=1.64)

            expected_off = (1.0 - p_low) * remaining_time

            mean_on = max(self._gap, self._ema_on_seconds)
            expected_sessions = max(0.0, remaining_time / max(mean_on, self._gap))
            expected_overhead_spot_only = min(0.35 * remaining_time, expected_sessions * restart_overhead)

            reserve_wait = expected_off + expected_overhead_spot_only
            if slack <= reserve_wait + safety:
                self._urgency = max(self._urgency, 1)

        if self._urgency >= 2:
            return ClusterType.ON_DEMAND

        on_streak_sec = self._on_streak_steps * gap
        off_streak_sec = self._off_streak_steps * gap
        mean_off = max(gap, self._ema_off_seconds)

        stable_on_seconds = max(2.0 * restart_overhead, 6.0 * 60.0)
        stable_on_seconds = min(stable_on_seconds, 20.0 * 60.0)

        patience_seconds = max(1.2 * restart_overhead, 3.0 * 60.0)
        patience_seconds = min(patience_seconds, 12.0 * 60.0)
        patience_seconds = min(patience_seconds, 0.25 * mean_off + restart_overhead)

        od_lock_seconds = max(4.0 * restart_overhead, 10.0 * 60.0)
        od_lock_seconds = min(od_lock_seconds, 45.0 * 60.0)
        od_lock_steps = max(1, int(math.ceil(od_lock_seconds / gap)))

        if self._urgency <= 0:
            if has_spot:
                if required_speed >= 0.965:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT
            else:
                if slack <= max(2.0 * restart_overhead + safety, 25.0 * 60.0):
                    self._urgency = 1
                else:
                    if off_streak_sec <= patience_seconds:
                        return ClusterType.NONE
                    self._urgency = 1

        if self._od_lock_steps > 0:
            self._od_lock_steps -= 1
            return ClusterType.ON_DEMAND

        if has_spot:
            if required_speed >= 0.97:
                return ClusterType.ON_DEMAND

            if last_cluster_type == ClusterType.ON_DEMAND:
                if on_streak_sec < stable_on_seconds:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            return ClusterType.SPOT

        # has_spot == False
        if last_cluster_type == ClusterType.ON_DEMAND:
            if slack >= 3.0 * 3600.0 and off_streak_sec <= min(patience_seconds, 6.0 * 60.0):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        if slack <= max(2.0 * restart_overhead + safety, 30.0 * 60.0):
            self._od_lock_steps = od_lock_steps
            return ClusterType.ON_DEMAND

        if off_streak_sec <= patience_seconds:
            return ClusterType.NONE

        self._od_lock_steps = od_lock_steps
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)