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

        self._p_ema = 0.7  # P(spot available)
        self._q_ema = 0.05  # P(interruption next step | we were on SPOT last step)
        self._spot_streak = 0
        self._od_locked = False

        self._alpha_p = 0.05
        self._alpha_q = 0.10

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _work_done_seconds(self) -> float:
        t = getattr(self, "task_done_time", None)
        if t is None:
            return 0.0
        if isinstance(t, (int, float)):
            return float(t)
        if not isinstance(t, (list, tuple)):
            return 0.0
        if not t:
            return 0.0

        total = 0.0
        all_numeric = True
        for x in t:
            if not isinstance(x, (int, float)):
                all_numeric = False
                break
        if all_numeric:
            for x in t:
                total += float(x)
            return total

        for seg in t:
            if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                a, b = seg[0], seg[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    total += float(b) - float(a)
            elif isinstance(seg, (int, float)):
                total += float(seg)
        return max(0.0, total)

    def _reserve_seconds(self, slack: float, remaining: float, gap: float) -> tuple[float, float]:
        p = min(0.999, max(0.001, float(self._p_ema)))
        q = min(0.999, max(0.0, float(self._q_ema)))
        ro = float(getattr(self, "restart_overhead", 0.0))

        base_reserve = max(6.0 * ro, 2.0 * gap)

        steps_remaining = remaining / max(gap, 1e-9)
        expected_interruptions = q * steps_remaining
        expected_overhead_time = expected_interruptions * ro
        overhead_reserve = min(6.0 * 3600.0, 0.7 * expected_overhead_time)

        unavail_penalty = max(0.0, 0.70 - p) * 6.0 * 3600.0
        lock_penalty = max(0.0, 0.50 - p) * 8.0 * 3600.0

        unavail_reserve = base_reserve + overhead_reserve + unavail_penalty
        lock_reserve = max(
            base_reserve * 1.3 + overhead_reserve + lock_penalty,
            8.0 * ro + 3.0 * gap,
        )

        if slack > 0:
            unavail_reserve = min(unavail_reserve, 0.75 * slack + base_reserve)
            lock_reserve = min(lock_reserve, 0.85 * slack + base_reserve)

        return unavail_reserve, lock_reserve

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        now = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        deadline = float(getattr(self, "deadline", now))
        task_duration = float(getattr(self, "task_duration", 0.0))

        done = self._work_done_seconds()
        remaining = max(0.0, task_duration - done)
        if remaining <= 1e-9:
            return ClusterType.NONE

        time_left = deadline - now
        if time_left <= 1e-9:
            return ClusterType.NONE

        a_p = self._alpha_p
        self._p_ema = (1.0 - a_p) * self._p_ema + a_p * (1.0 if has_spot else 0.0)

        if last_cluster_type == ClusterType.SPOT:
            interrupted = 1.0 if not has_spot else 0.0
            a_q = self._alpha_q
            self._q_ema = (1.0 - a_q) * self._q_ema + a_q * interrupted

        if has_spot:
            self._spot_streak += 1
        else:
            self._spot_streak = 0

        slack = time_left - remaining
        unavail_reserve, lock_reserve = self._reserve_seconds(slack, remaining, gap)

        ro = float(getattr(self, "restart_overhead", 0.0))
        if slack <= 0.0 or time_left <= remaining + max(2.0 * ro, 2.0 * gap) or time_left <= remaining + lock_reserve:
            self._od_locked = True

        if self._od_locked:
            return ClusterType.ON_DEMAND

        if has_spot:
            if slack < lock_reserve:
                return ClusterType.ON_DEMAND

            if last_cluster_type == ClusterType.ON_DEMAND:
                switch_back_threshold = unavail_reserve + 2.0 * gap + ro
                if self._spot_streak >= 2 and slack > switch_back_threshold:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND

            return ClusterType.SPOT

        # has_spot == False
        if last_cluster_type == ClusterType.ON_DEMAND:
            if slack > unavail_reserve + 3.0 * gap:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        if slack > unavail_reserve:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
