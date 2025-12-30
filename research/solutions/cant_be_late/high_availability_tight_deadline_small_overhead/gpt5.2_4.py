import math
from typing import Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._done_sum = 0.0
        self._done_len = 0

        self._od_locked = False

        self._streak_has_spot: Optional[bool] = None
        self._streak_steps = 0
        self._spot_true_streak_steps = 0

        self._ema_up = 3600.0
        self._ema_down = 1800.0
        self._alpha = 0.2

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_done(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if not lst:
            return 0.0
        n = len(lst)
        if n > self._done_len:
            self._done_sum += float(sum(lst[self._done_len :]))
            self._done_len = n
        return self._done_sum

    def _update_spot_stats(self, has_spot: bool, gap: float) -> None:
        if self._streak_has_spot is None:
            self._streak_has_spot = has_spot
            self._streak_steps = 1
        else:
            if has_spot == self._streak_has_spot:
                self._streak_steps += 1
            else:
                dur = float(self._streak_steps) * gap
                if self._streak_has_spot:
                    self._ema_up = self._alpha * dur + (1.0 - self._alpha) * self._ema_up
                else:
                    self._ema_down = self._alpha * dur + (1.0 - self._alpha) * self._ema_down
                self._streak_has_spot = has_spot
                self._streak_steps = 1

        if has_spot:
            self._spot_true_streak_steps += 1
        else:
            self._spot_true_streak_steps = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 60.0

        self._update_spot_stats(bool(has_spot), gap)

        done = self._update_done()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining = max(0.0, task_duration - done)
        if remaining <= 1e-9:
            return ClusterType.NONE

        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = deadline - now

        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        overhead = max(0.0, overhead)

        hard_reserve = max(900.0, 2.0 * overhead + 3.0 * gap)
        od_lock_reserve = max(1800.0, 4.0 * overhead + 6.0 * gap)

        slack = time_left - remaining

        if slack <= od_lock_reserve:
            self._od_locked = True

        if self._od_locked:
            return ClusterType.ON_DEMAND

        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT

            confirm_steps = 2
            expected_up = max(self._ema_up, gap)
            min_up_to_switch = max(3.0 * overhead + 2.0 * gap, 0.25 * 3600.0)

            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._spot_true_streak_steps >= confirm_steps and expected_up >= min_up_to_switch and slack > (hard_reserve + overhead):
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND

            # last_cluster_type == NONE (or anything else)
            return ClusterType.SPOT

        # no spot
        # Pause if still safe to finish later by switching to on-demand, else use on-demand now.
        # Conservative: assume starting OD next step from NONE costs one overhead.
        if slack > (hard_reserve + gap + overhead):
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)