import math
from collections import deque
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._initialized = False

        self._prev_has_spot: Optional[bool] = None
        self._cur_status_len_steps: int = 0

        self._ema_up_seconds: Optional[float] = None
        self._ema_down_seconds: Optional[float] = None
        self._ema_alpha: float = 0.25

        self._spot_hist = deque(maxlen=600)
        self._od_start_elapsed: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _safe_float(self, x: Any) -> Optional[float]:
        try:
            if x is None:
                return None
            if isinstance(x, bool):
                return None
            return float(x)
        except Exception:
            return None

    def _done_work_seconds(self) -> float:
        td = getattr(self, "task_duration", 0.0)
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            done = float(tdt)
            if math.isnan(done) or math.isinf(done):
                return 0.0
            return max(0.0, min(done, float(td)))

        if not isinstance(tdt, (list, tuple, deque)):
            v = self._safe_float(tdt)
            if v is None:
                return 0.0
            return max(0.0, min(v, float(td)))

        if len(tdt) == 0:
            return 0.0

        nums = []
        for x in tdt:
            v = self._safe_float(x)
            if v is not None and not math.isnan(v) and not math.isinf(v):
                nums.append(v)

        if not nums:
            return 0.0

        s = sum(nums)
        last = nums[-1]
        td_f = float(td) if td is not None else 0.0
        if td_f > 0.0 and s > td_f * 1.05:
            done = last
        else:
            done = s

        if math.isnan(done) or math.isinf(done):
            done = 0.0
        if td_f > 0.0:
            done = min(done, td_f)
        return max(0.0, done)

    def _update_spot_run_stats(self, has_spot: bool) -> None:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 1.0

        self._spot_hist.append(1 if has_spot else 0)

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._cur_status_len_steps = 1
            return

        if has_spot == self._prev_has_spot:
            self._cur_status_len_steps += 1
            return

        run_seconds = self._cur_status_len_steps * gap
        if self._prev_has_spot:
            if self._ema_up_seconds is None:
                self._ema_up_seconds = run_seconds
            else:
                a = self._ema_alpha
                self._ema_up_seconds = a * run_seconds + (1.0 - a) * self._ema_up_seconds
        else:
            if self._ema_down_seconds is None:
                self._ema_down_seconds = run_seconds
            else:
                a = self._ema_alpha
                self._ema_down_seconds = a * run_seconds + (1.0 - a) * self._ema_down_seconds

        self._prev_has_spot = has_spot
        self._cur_status_len_steps = 1

    def _spot_availability_hat(self) -> float:
        if not self._spot_hist:
            return 0.6
        return sum(self._spot_hist) / float(len(self._spot_hist))

    def _should_switch_back_to_spot(self, slack: float, has_spot: bool, last_cluster_type: ClusterType) -> bool:
        if not has_spot:
            return False
        if last_cluster_type != ClusterType.ON_DEMAND:
            return True

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 1.0

        confirm_seconds = max(2.0 * gap, 300.0)
        spot_avail_run_seconds = (self._cur_status_len_steps * gap) if has_spot else 0.0
        if spot_avail_run_seconds < confirm_seconds:
            return False

        p_hat = self._spot_availability_hat()
        if p_hat < 0.55:
            return False

        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        min_slack = max(2.5 * 3600.0, 6.0 * ro + 4.0 * gap)
        if slack < min_slack:
            return False

        avg_up = self._ema_up_seconds
        if avg_up is not None:
            if avg_up < max(3600.0, 6.0 * ro):
                return False

        if self._od_start_elapsed is not None:
            elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
            if elapsed - self._od_start_elapsed < max(1800.0, 2.0 * ro):
                return False

        return True

    def _should_wait_for_spot(self, slack: float) -> bool:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 1.0
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        reserve = max(2.0 * ro + 2.0 * gap, 900.0)
        wait_budget = slack - reserve
        if wait_budget <= gap:
            return False

        avg_down = self._ema_down_seconds
        if avg_down is None:
            avg_down = 20.0 * 60.0

        cur_down_seconds = self._cur_status_len_steps * gap
        pred_remaining = max(0.0, avg_down - cur_down_seconds)

        max_wait = min(1800.0, 0.2 * max(0.0, slack))
        pred_remaining = min(pred_remaining, max_wait)

        if pred_remaining <= gap:
            return True
        if pred_remaining <= wait_budget:
            return True
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_spot_run_stats(has_spot)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 1.0
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._done_work_seconds()
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(0.0, td - done)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)
        slack = time_left - remaining_work

        reserve = max(2.0 * ro + 2.0 * gap, 900.0)
        if slack <= reserve:
            if last_cluster_type != ClusterType.ON_DEMAND and self._od_start_elapsed is None:
                self._od_start_elapsed = elapsed
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            if self._should_switch_back_to_spot(slack, has_spot, last_cluster_type):
                self._od_start_elapsed = None
                return ClusterType.SPOT
            if self._od_start_elapsed is None:
                self._od_start_elapsed = elapsed
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self._should_wait_for_spot(slack):
            return ClusterType.NONE

        if self._od_start_elapsed is None:
            self._od_start_elapsed = elapsed
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)