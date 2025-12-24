import math
from collections import deque
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args

        self._initialized = False

        self._p_ema = 0.2
        self._p_alpha = 0.05

        self._prev_has_spot: Optional[bool] = None
        self._up_streak = 0
        self._down_streak = 0
        self._up_len_ema = 6.0
        self._down_len_ema = 6.0
        self._len_alpha = 0.15

        self._locked_od = False
        self._od_min_run_until = 0.0

        self._recent_avail = deque(maxlen=256)

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _safe_float(self, x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _get_work_done_seconds(self) -> float:
        # Try common attributes first.
        for obj in (self, getattr(self, "env", None)):
            if obj is None:
                continue
            for name in (
                "task_done_seconds",
                "task_done",
                "completed_seconds",
                "work_done_seconds",
                "done_seconds",
            ):
                if hasattr(obj, name):
                    v = getattr(obj, name)
                    if isinstance(v, (int, float)):
                        return float(v)

        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)

        total = 0.0
        if isinstance(tdt, (list, tuple, deque)):
            for seg in tdt:
                if seg is None:
                    continue
                if isinstance(seg, (int, float)):
                    total += float(seg)
                    continue
                if isinstance(seg, dict):
                    if "duration" in seg and isinstance(seg["duration"], (int, float)):
                        total += float(seg["duration"])
                        continue
                    if "start" in seg and "end" in seg:
                        try:
                            total += abs(float(seg["end"]) - float(seg["start"]))
                        except Exception:
                            pass
                        continue
                if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    a, b = seg[0], seg[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        total += abs(float(b) - float(a))
                        continue
        return total

    def _remaining_work_seconds(self) -> float:
        dur = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        done = self._get_work_done_seconds()
        rem = dur - done
        return rem if rem > 0.0 else 0.0

    def _ensure_initialized(self):
        if self._initialized:
            return
        self._initialized = True

        gap = self._safe_float(getattr(self.env, "gap_seconds", 300.0), 300.0)
        gap = max(gap, 1.0)

        # Tune EMA based on gap length.
        # ~2 hours half-life-ish for availability estimation.
        steps_2h = max(1.0, (2.0 * 3600.0) / gap)
        self._p_alpha = 1.0 - math.exp(math.log(0.5) / steps_2h)
        self._p_alpha = min(max(self._p_alpha, 0.01), 0.2)

        # Slightly faster adaptation for contiguous period lengths.
        steps_1h = max(1.0, (1.0 * 3600.0) / gap)
        self._len_alpha = 1.0 - math.exp(math.log(0.5) / steps_1h)
        self._len_alpha = min(max(self._len_alpha, 0.05), 0.35)

    def _update_spot_stats(self, has_spot: bool):
        self._recent_avail.append(1 if has_spot else 0)

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._up_streak = 1 if has_spot else 0
            self._down_streak = 0 if has_spot else 1
        else:
            if has_spot:
                self._up_streak += 1
                self._down_streak = 0
            else:
                self._down_streak += 1
                self._up_streak = 0

            # Transition updates for contiguous-length EMAs.
            if self._prev_has_spot and not has_spot:
                # up -> down
                up_len = max(1, self._up_streak_prev if hasattr(self, "_up_streak_prev") else 1)
                self._up_len_ema = (1.0 - self._len_alpha) * self._up_len_ema + self._len_alpha * float(up_len)
            elif (not self._prev_has_spot) and has_spot:
                # down -> up
                down_len = max(1, self._down_streak_prev if hasattr(self, "_down_streak_prev") else 1)
                self._down_len_ema = (1.0 - self._len_alpha) * self._down_len_ema + self._len_alpha * float(down_len)

            self._prev_has_spot = has_spot

        # Store previous streak lengths for the next transition update.
        self._up_streak_prev = self._up_streak
        self._down_streak_prev = self._down_streak

        x = 1.0 if has_spot else 0.0
        self._p_ema = self._p_alpha * x + (1.0 - self._p_alpha) * self._p_ema

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        now = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        gap = self._safe_float(getattr(self.env, "gap_seconds", 300.0), 300.0)
        gap = max(gap, 1.0)

        self._update_spot_stats(has_spot)

        remaining_work = self._remaining_work_seconds()
        if remaining_work <= 1e-9:
            self._locked_od = False
            return ClusterType.NONE

        deadline = self._safe_float(getattr(self, "deadline", float("inf")), float("inf"))
        remaining_time = deadline - now
        if remaining_time <= 0.0:
            return ClusterType.NONE

        slack = remaining_time - remaining_work
        ro = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        ro = max(ro, 0.0)

        safety = max(3.0 * ro, 600.0, 0.5 * gap)
        critical_slack = max(3600.0, 2.0 * safety)

        # Near the end or if slack is tight, lock into on-demand to avoid deadline risk.
        if (not self._locked_od) and (slack <= critical_slack or remaining_time <= remaining_work + safety):
            self._locked_od = True
            self._od_min_run_until = max(self._od_min_run_until, now + 1800.0)

        if self._locked_od:
            return ClusterType.ON_DEMAND

        # Minimum on-demand run time to avoid thrashing.
        if last_cluster_type == ClusterType.ON_DEMAND and now < self._od_min_run_until:
            return ClusterType.ON_DEMAND

        # Expected contiguous durations (rough heuristics).
        expected_up_time = max(1.0, self._up_len_ema) * gap
        expected_down_time = max(1.0, self._down_len_ema) * gap

        # Estimate time-to-spot when currently down.
        p = max(self._p_ema, 0.02)
        expected_wait_time = gap / p
        # If currently in a long down streak, bias expected wait up.
        expected_wait_time *= min(6.0, 1.0 + 0.15 * float(self._down_streak))
        expected_wait_time = max(expected_wait_time, expected_down_time)
        expected_wait_time = min(expected_wait_time, 3.0 * 3600.0)

        def can_afford_idle_one_step() -> bool:
            # If we idle this step, slack shrinks by gap. Also, starting later will likely incur a restart overhead.
            return (slack - gap - ro) >= safety

        if has_spot:
            # If we are currently on-demand, only switch to spot if it likely stays up long enough.
            min_spot_up_to_switch = max(3.0 * ro + gap, 900.0)
            if last_cluster_type == ClusterType.ON_DEMAND:
                if expected_up_time < min_spot_up_to_switch:
                    return ClusterType.ON_DEMAND
                # Ensure switching overhead won't make slack unsafe.
                if (slack - ro) < safety:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            # From NONE or SPOT: generally use SPOT if available, but avoid very short spot bursts when slack is limited.
            min_spot_up_to_start = max(2.5 * ro + gap, 600.0)
            if last_cluster_type == ClusterType.NONE and expected_up_time < min_spot_up_to_start and slack < (2.0 * 3600.0):
                self._od_min_run_until = max(self._od_min_run_until, now + 1800.0)
                return ClusterType.ON_DEMAND

            return ClusterType.SPOT

        # No spot available.
        if last_cluster_type == ClusterType.ON_DEMAND:
            # If we have plenty of slack, we can stop paying and wait.
            if slack >= (2.5 * 3600.0 + safety) and can_afford_idle_one_step():
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Not currently on-demand and spot is down: decide whether to wait or start on-demand.
        if not can_afford_idle_one_step():
            self._od_min_run_until = max(self._od_min_run_until, now + 1800.0)
            return ClusterType.ON_DEMAND

        # Wait if expected spot return is soon enough relative to slack.
        if slack >= (expected_wait_time + safety) and slack >= (1800.0 + safety):
            return ClusterType.NONE

        self._od_min_run_until = max(self._od_min_run_until, now + 1800.0)
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
