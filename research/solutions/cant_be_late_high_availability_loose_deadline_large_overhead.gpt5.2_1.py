import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_spot"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            super().__init__()
        self.args = args
        self._reset_episode_state()

        # Tunables (seconds)
        self._safety_slack = 2.0 * 3600.0  # switch to OD a bit early
        self._min_lcb = 0.08               # pessimistic minimum spot availability assumption
        self._z = 2.25                     # ~98.8% two-sided; used for LCB
        self._max_down_multiplier = 1.25   # buffer against observed long outages
        self._commit_lock_in = True        # once OD is chosen, stay on OD until done

    def _reset_episode_state(self):
        self._last_elapsed = None
        self._committed_od = False

        self._hist_total = 0
        self._hist_spot = 0

        self._prev_has_spot = None
        self._cur_up = 0.0
        self._cur_down = 0.0
        self._max_up = 0.0
        self._max_down = 0.0

        self._td_len = 0
        self._td_sum = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _seg_duration(seg: Any) -> float:
        if seg is None:
            return 0.0
        if isinstance(seg, (int, float)):
            return float(seg)
        if isinstance(seg, (tuple, list)) and len(seg) == 2:
            a, b = seg
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                return float(max(0.0, b - a))
            return 0.0
        if isinstance(seg, dict):
            if "duration" in seg and isinstance(seg["duration"], (int, float)):
                return float(seg["duration"])
            if "start" in seg and "end" in seg:
                a, b = seg["start"], seg["end"]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    return float(max(0.0, b - a))
            return 0.0
        return 0.0

    def _get_done(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)
        if isinstance(td, list):
            l = len(td)
            if l < self._td_len:
                self._td_len = 0
                self._td_sum = 0.0
            if l > self._td_len:
                add = 0.0
                for seg in td[self._td_len:]:
                    add += self._seg_duration(seg)
                self._td_sum += add
                self._td_len = l
            return self._td_sum
        return 0.0

    def _availability_lcb(self) -> float:
        n = self._hist_total
        if n <= 0:
            return self._min_lcb
        p = self._hist_spot / n
        var = p * (1.0 - p) / max(1.0, float(n))
        lcb = p - self._z * math.sqrt(max(0.0, var))
        if n < 60:
            # be more conservative early
            lcb *= n / 60.0
        return max(self._min_lcb, min(1.0, lcb))

    def _episode_maybe_reset(self):
        try:
            elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        except Exception:
            elapsed = 0.0
        if self._last_elapsed is None:
            self._last_elapsed = elapsed
            if elapsed == 0.0:
                self._reset_episode_state()
                self._last_elapsed = elapsed
            return
        if elapsed < self._last_elapsed or (elapsed == 0.0 and self._last_elapsed > 0.0):
            self._reset_episode_state()
            self._last_elapsed = elapsed
        else:
            self._last_elapsed = elapsed

    def _update_availability_stats(self, has_spot: bool, gap: float):
        self._hist_total += 1
        if has_spot:
            self._hist_spot += 1

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot

        if has_spot:
            self._cur_up += gap
            self._cur_down = 0.0
            if self._cur_up > self._max_up:
                self._max_up = self._cur_up
        else:
            self._cur_down += gap
            self._cur_up = 0.0
            if self._cur_down > self._max_down:
                self._max_down = self._cur_down

        self._prev_has_spot = has_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._episode_maybe_reset()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        self._update_availability_stats(has_spot, gap)

        task_duration = float(getattr(self, "task_duration", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        done = self._get_done()
        remaining_work = max(0.0, task_duration - done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)

        # If already committed to on-demand, stay there until completion.
        if self._committed_od and self._commit_lock_in:
            return ClusterType.ON_DEMAND

        # Hard feasibility: if we need nearly all remaining time even on OD, go OD now.
        hard_buffer = 3.0 * restart_overhead + gap
        if time_left <= remaining_work + hard_buffer:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Risk-aware: if spot likely can't finish in time, commit to OD.
        lcb = self._availability_lcb()
        down_buffer = self._max_down_multiplier * max(self._max_down, 0.0)

        # Conservative wall-clock time to finish if we only make progress when spot is available.
        # This assumes we choose NONE when spot is unavailable (no progress).
        # Add buffers for restarts and observed outages.
        spot_finish_time_est = (remaining_work / max(lcb, self._min_lcb)) + 2.0 * restart_overhead + down_buffer

        if spot_finish_time_est >= max(0.0, time_left - self._safety_slack):
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available; pause when it's not.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)