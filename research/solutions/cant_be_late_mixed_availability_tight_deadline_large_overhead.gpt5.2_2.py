from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional


try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:  # minimal fallback
        def __init__(self, *args, **kwargs):
            self.env = type("Env", (), {"elapsed_seconds": 0.0, "gap_seconds": 60.0, "cluster_type": ClusterType.NONE})()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def _is_non_decreasing(seq) -> bool:
    try:
        for i in range(len(seq) - 1):
            if seq[i] > seq[i + 1]:
                return False
        return True
    except Exception:
        return False


@dataclass
class _SpotStats:
    steps: int = 0
    spot_steps: int = 0
    flips: int = 0

    prev_has_spot: Optional[bool] = None

    avail_streak_cur: int = 0
    unavail_streak_cur: int = 0

    avail_streak_sum: int = 0
    avail_streak_cnt: int = 0

    unavail_streak_sum: int = 0
    unavail_streak_cnt: int = 0

    interruptions: int = 0

    waited_seconds_total: float = 0.0
    waited_seconds_unavail_cur: float = 0.0


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        self.args = args
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._stats = _SpotStats()
        self._init_done = False
        self._od_commit = False

        self._gap = None

    def solve(self, spec_path: str) -> "Solution":
        self._stats = _SpotStats()
        self._init_done = False
        self._od_commit = False
        self._gap = None
        return self

    def _done_seconds(self) -> float:
        t = getattr(self, "task_done_time", None)
        if not t:
            return 0.0

        try:
            first = t[0]
        except Exception:
            return 0.0

        # Numeric list: could be incremental or cumulative
        if _is_number(first):
            nums = []
            try:
                for x in t:
                    if _is_number(x):
                        nums.append(float(x))
                    else:
                        break
            except Exception:
                return 0.0

            if not nums:
                return 0.0

            s = float(sum(nums))
            last = float(nums[-1])
            td = float(getattr(self, "task_duration", 0.0) or 0.0)

            # Heuristic: if list appears cumulative (non-decreasing, last near duration, sum much larger),
            # use last; else use sum.
            if len(nums) >= 2 and _is_non_decreasing(nums) and td > 0:
                if last <= td * 1.10 and s >= max(td * 1.50, last * 1.50):
                    return max(0.0, last)
            return max(0.0, s)

        # List of segments: tuple/list/dict
        done = 0.0
        try:
            for seg in t:
                if isinstance(seg, (tuple, list)) and len(seg) >= 2 and _is_number(seg[0]) and _is_number(seg[1]):
                    done += float(seg[1]) - float(seg[0])
                elif isinstance(seg, dict):
                    a = seg.get("start", seg.get("s", seg.get("begin")))
                    b = seg.get("end", seg.get("e", seg.get("finish")))
                    if _is_number(a) and _is_number(b):
                        done += float(b) - float(a)
        except Exception:
            return max(0.0, float(done))
        return max(0.0, float(done))

    def _update_stats(self, last_cluster_type: ClusterType, has_spot: bool) -> None:
        st = self._stats
        st.steps += 1
        if has_spot:
            st.spot_steps += 1

        if st.prev_has_spot is not None and st.prev_has_spot != has_spot:
            st.flips += 1

        if has_spot:
            if st.unavail_streak_cur > 0:
                st.unavail_streak_sum += st.unavail_streak_cur
                st.unavail_streak_cnt += 1
                st.unavail_streak_cur = 0
                st.waited_seconds_unavail_cur = 0.0
            st.avail_streak_cur += 1
        else:
            if st.avail_streak_cur > 0:
                st.avail_streak_sum += st.avail_streak_cur
                st.avail_streak_cnt += 1
                st.avail_streak_cur = 0
            st.unavail_streak_cur += 1

        # Spot interruption signal: we wanted spot last step but spot is unavailable now.
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            st.interruptions += 1

        st.prev_has_spot = has_spot

    def _p_est(self) -> float:
        st = self._stats
        # Laplace smoothing
        return (st.spot_steps + 1.0) / (st.steps + 2.0)

    def _avg_unavail_seconds(self, gap: float) -> float:
        st = self._stats
        if st.unavail_streak_cnt <= 0:
            return 10.0 * gap
        return (st.unavail_streak_sum / st.unavail_streak_cnt) * gap

    def _avg_avail_seconds(self, gap: float) -> float:
        st = self._stats
        if st.avail_streak_cnt <= 0:
            return 10.0 * gap
        return (st.avail_streak_sum / st.avail_streak_cnt) * gap

    def _interruptions_per_hour(self, now: float) -> float:
        st = self._stats
        if now <= 0:
            return 0.0
        return st.interruptions / (now / 3600.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        if env is None:
            return ClusterType.ON_DEMAND if not has_spot else ClusterType.SPOT

        now = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 60.0) or 60.0)
        if gap <= 0:
            gap = 60.0
        self._gap = gap

        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if ro < 0:
            ro = 0.0

        done = self._done_seconds()
        remaining_work = max(0.0, td - done)
        time_left = deadline - now
        slack = time_left - remaining_work

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        if time_left <= 0.0:
            return ClusterType.NONE

        self._update_stats(last_cluster_type, has_spot)
        p = self._p_est()

        # Risk-aware reserve slack: keep some buffer to absorb restart overhead + uncertainty.
        base_reserve = max(2.0 * ro, 1800.0, 3.0 * gap)  # at least 30 minutes, plus overhead
        risk_scale = 7200.0  # up to 2 hours extra buffer at very low availability
        risk_margin = (1.0 - p) * risk_scale
        intr_rate = self._interruptions_per_hour(now)
        risk_margin += min(3.0, intr_rate) * ro  # cap influence of early noisy estimates
        reserve_slack = base_reserve + risk_margin

        critical = slack <= reserve_slack

        # Burn-in periods for committing to OD in very unreliable traces.
        burn_in = max(3600.0, 30.0 * gap)
        quick_burn_in = max(1800.0, 15.0 * gap)

        avg_avail_s = self._avg_avail_seconds(gap)
        avg_unavail_s = self._avg_unavail_seconds(gap)

        if not self._od_commit:
            # Commit if we're getting close to deadline (avoid late risk / switching).
            if critical and slack <= reserve_slack + ro:
                self._od_commit = True
            # Commit early if availability is very low after some observation.
            elif now >= quick_burn_in and p < 0.18:
                self._od_commit = True
            elif now >= burn_in:
                if p < 0.28:
                    self._od_commit = True
                elif p < 0.38 and avg_avail_s < max(2.0 * gap, 0.5 * ro):
                    self._od_commit = True
                elif intr_rate >= 4.0:
                    self._od_commit = True

        if self._od_commit:
            return ClusterType.ON_DEMAND

        # Prefer spot when available unless we're too close to deadline.
        if has_spot:
            if critical:
                return ClusterType.ON_DEMAND

            # Avoid frequent switches: if currently on OD, only switch back to spot when
            # spot has been stable for a bit and we have enough slack to absorb restart.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._stats.avail_streak_cur >= 2 and slack >= reserve_slack + ro + gap:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND

            return ClusterType.SPOT

        # No spot: use slack budget to wait (NONE) when safe; else use on-demand.
        if critical:
            return ClusterType.ON_DEMAND

        wait_budget = slack - reserve_slack
        if wait_budget >= gap:
            # Only wait if unavailability streaks are typically short (or we are still early in one).
            unavail_len_s = self._stats.unavail_streak_cur * gap
            max_wait_this_streak = min(max(3.0 * gap, 0.5 * avg_unavail_s), 3600.0)
            if self._stats.waited_seconds_unavail_cur + gap <= max_wait_this_streak and unavail_len_s <= max(2.0 * avg_unavail_s, 6.0 * gap):
                self._stats.waited_seconds_total += gap
                self._stats.waited_seconds_unavail_cur += gap
                return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)