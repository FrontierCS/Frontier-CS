import argparse
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_guard_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._inited = False

        self._steps = 0
        self._spot_avail_steps = 0

        self._prev_has_spot: Optional[bool] = None
        self._streak_len_steps = 0

        self._ema_avail: Optional[float] = None
        self._ema_unavail: Optional[float] = None
        self._ema_alpha = 0.2
        self._avail_streaks = 0
        self._unavail_streaks = 0

        self._committed_od = False
        self._od_until = 0.0

        self._idle_seconds = 0.0
        self._max_idle_seconds: Optional[float] = None

        self._tdt_len = 0
        self._done_cache = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _init_if_needed(self) -> None:
        if self._inited:
            return
        self._inited = True

        slack_total = float(self.deadline) - float(self.task_duration)
        if slack_total < 0:
            slack_total = 0.0
        self._max_idle_seconds = 0.65 * slack_total

        default = 1800.0
        self._ema_avail = default
        self._ema_unavail = default

    def _update_streak_ema(self, has_spot: bool) -> None:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 1.0

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._streak_len_steps = 1
            return

        if has_spot == self._prev_has_spot:
            self._streak_len_steps += 1
            return

        streak_seconds = self._streak_len_steps * gap
        if self._prev_has_spot:
            self._avail_streaks += 1
            self._ema_avail = (
                self._ema_alpha * streak_seconds + (1.0 - self._ema_alpha) * (self._ema_avail or streak_seconds)
            )
        else:
            self._unavail_streaks += 1
            self._ema_unavail = (
                self._ema_alpha * streak_seconds + (1.0 - self._ema_alpha) * (self._ema_unavail or streak_seconds)
            )

        self._prev_has_spot = has_spot
        self._streak_len_steps = 1

    def _seg_to_duration(self, seg: Any) -> float:
        try:
            if seg is None:
                return 0.0
            if isinstance(seg, (int, float)):
                return float(seg)
            if isinstance(seg, dict):
                if "duration" in seg:
                    return float(seg["duration"])
                if "start" in seg and "end" in seg:
                    return float(seg["end"]) - float(seg["start"])
                return 0.0
            if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                return float(seg[1]) - float(seg[0])
        except Exception:
            return 0.0
        return 0.0

    def _done_work_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            self._tdt_len = 0
            self._done_cache = 0.0
            return 0.0

        try:
            n = len(tdt)
        except Exception:
            return float(self._done_cache)

        if n < self._tdt_len:
            total = 0.0
            for seg in tdt:
                total += self._seg_to_duration(seg)
            self._tdt_len = n
            self._done_cache = max(0.0, total)
            return self._done_cache

        if n > self._tdt_len:
            add = 0.0
            for seg in tdt[self._tdt_len : n]:
                add += self._seg_to_duration(seg)
            self._tdt_len = n
            self._done_cache = max(0.0, self._done_cache + add)

        return self._done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 1.0

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        self._steps += 1
        if has_spot:
            self._spot_avail_steps += 1
        self._update_streak_ema(has_spot)

        done = self._done_work_seconds()
        task_dur = float(self.task_duration)
        if done < 0:
            done = 0.0
        if done > task_dur:
            done = task_dur

        remaining_work = task_dur - done
        deadline = float(self.deadline)
        time_remaining = deadline - elapsed

        overhead = float(self.restart_overhead)
        overhead_to_start_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead

        reserve = max(3.0 * overhead, 8.0 * gap)
        final_buffer = max(2.0 * overhead, 8.0 * gap)

        slack_to_od = time_remaining - (remaining_work + overhead_to_start_od)

        if not self._committed_od:
            if time_remaining <= remaining_work + overhead_to_start_od + final_buffer:
                self._committed_od = True

        if self._committed_od:
            self._od_until = max(self._od_until, elapsed + max(overhead, 4.0 * gap))
            return ClusterType.ON_DEMAND

        p_est = self._spot_avail_steps / self._steps if self._steps > 0 else 0.0

        ema_avail = float(self._ema_avail or 1800.0)
        ema_unavail = float(self._ema_unavail or 1800.0)

        if self._avail_streaks < 2:
            ema_avail = max(ema_avail, 1200.0)
        if self._unavail_streaks < 2:
            ema_unavail = max(ema_unavail, 1200.0)

        spot_bad = (self._avail_streaks >= 3) and (ema_avail < 0.85 * overhead) and (p_est < 0.25)

        if not has_spot:
            if slack_to_od <= 0.0:
                if last_cluster_type != ClusterType.ON_DEMAND:
                    self._od_until = elapsed + max(overhead, 4.0 * gap)
                return ClusterType.ON_DEMAND

            expected_unavail = ema_unavail
            if self._unavail_streaks < 1:
                expected_unavail = max(expected_unavail, gap / max(p_est, 0.10))

            can_wait = slack_to_od > reserve + 1.2 * expected_unavail
            if self._max_idle_seconds is not None and self._idle_seconds >= self._max_idle_seconds:
                can_wait = False

            if can_wait:
                self._idle_seconds += gap
                return ClusterType.NONE

            if last_cluster_type != ClusterType.ON_DEMAND:
                self._od_until = elapsed + max(overhead, 4.0 * gap)
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.SPOT:
            return ClusterType.SPOT

        if spot_bad:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._od_until = elapsed + max(overhead, 4.0 * gap)
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.NONE:
            return ClusterType.SPOT

        if last_cluster_type == ClusterType.ON_DEMAND:
            if elapsed < self._od_until:
                return ClusterType.ON_DEMAND

            min_avail_to_switch = max(overhead, 3.0 * gap)
            if slack_to_od > reserve and ema_avail >= min_avail_to_switch and p_est >= 0.08:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)