import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbl_safe_hybrid_v2"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self.args = args
        self._reset_internal()

    def _reset_internal(self):
        self._mode = "SPOT_PREF"  # or "OD"
        self._mode_since = 0.0
        self._had_od = False

        self._ewma_p = 0.25
        self._alpha = 0.03

        self._spot_streak = 0.0
        self._no_spot_streak = 0.0

        self._spot_loss_count = 0
        self._spot_run_seconds = 0.0

        self._last_elapsed = None
        self._initialized = True

    def solve(self, spec_path: str) -> "Solution":
        self._reset_internal()
        return self

    def _compute_done_work_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            if hasattr(self, "env"):
                for name in ("task_done_seconds", "done_seconds", "task_done"):
                    val = getattr(self.env, name, None)
                    if isinstance(val, (int, float)):
                        return float(val)
            return 0.0

        if isinstance(tdt, (int, float)):
            return float(tdt)

        total = 0.0
        try:
            for seg in tdt:
                if seg is None:
                    continue
                if isinstance(seg, (int, float)):
                    total += float(seg)
                elif isinstance(seg, (tuple, list)) and len(seg) == 2:
                    try:
                        a = float(seg[0])
                        b = float(seg[1])
                        if b >= a:
                            total += (b - a)
                    except Exception:
                        pass
                elif isinstance(seg, dict):
                    if "duration" in seg:
                        try:
                            total += float(seg["duration"])
                        except Exception:
                            pass
                    elif "start" in seg and "end" in seg:
                        try:
                            a = float(seg["start"])
                            b = float(seg["end"])
                            if b >= a:
                                total += (b - a)
                        except Exception:
                            pass
        except TypeError:
            return 0.0

        return total

    def _maybe_episode_reset(self, done_work: float):
        if not hasattr(self, "env"):
            return
        el = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)

        if self._last_elapsed is not None and el < self._last_elapsed - 1e-6:
            self._reset_internal()
            self._mode_since = el
            return

        if el <= max(1e-9, 0.5 * gap) and done_work <= 1e-6:
            if self._last_elapsed is None or self._last_elapsed > 0.5 * gap:
                self._reset_internal()
                self._mode_since = el

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done_work = self._compute_done_work_seconds()
        if not getattr(self, "_initialized", False):
            self._reset_internal()

        self._maybe_episode_reset(done_work)

        el = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        self._last_elapsed = el

        hs = 1.0 if has_spot else 0.0
        self._ewma_p = self._alpha * hs + (1.0 - self._alpha) * self._ewma_p

        if has_spot:
            self._spot_streak += gap
            self._no_spot_streak = 0.0
        else:
            self._no_spot_streak += gap
            self._spot_streak = 0.0

        if last_cluster_type == ClusterType.SPOT:
            self._spot_run_seconds += gap
            if not has_spot:
                self._spot_loss_count += 1

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        remaining_work = max(0.0, task_duration - done_work)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        remaining_time = max(0.0, deadline - el)
        slack = remaining_time - remaining_work

        base_buffer = 2.0 * restart_overhead + 2.0 * gap
        emergency_buffer = restart_overhead + 2.0 * gap

        if self._spot_run_seconds > 0.0:
            interrupt_rate = self._spot_loss_count / self._spot_run_seconds
        else:
            interrupt_rate = 0.0
        expected_overhead_remaining = min(remaining_time, interrupt_rate * remaining_work * restart_overhead)
        wait_threshold = base_buffer + 0.5 * expected_overhead_remaining

        if slack <= emergency_buffer:
            if self._mode != "OD":
                self._mode = "OD"
                self._mode_since = el
                self._had_od = True
            return ClusterType.ON_DEMAND

        if self._mode == "OD":
            time_in_mode = el - self._mode_since
            if has_spot:
                streak_ok = self._spot_streak >= 3600.0
                revert_slack = 3.0 * restart_overhead + 4.0 * gap
                work_ok = remaining_work >= 6.0 * 3600.0
                time_ok = remaining_time >= 10.0 * 3600.0
                cooldown_ok = time_in_mode >= 3600.0
                if streak_ok and work_ok and time_ok and cooldown_ok and slack >= revert_slack:
                    self._mode = "SPOT_PREF"
                    self._mode_since = el
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # SPOT_PREF mode
        if has_spot:
            return ClusterType.SPOT

        # No spot available
        if self._had_od:
            self._mode = "OD"
            self._mode_since = el
            return ClusterType.ON_DEMAND

        if slack <= wait_threshold:
            self._mode = "OD"
            self._mode_since = el
            self._had_od = True
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)