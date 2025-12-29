import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_slack_buffer_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._initialized = False

        self._p_spot = 0.5
        self._ema_alpha = 0.02

        self._spot_up_streak = 0
        self._spot_down_streak = 0

        self._done_cache_len = 0
        self._done_cache_sum = 0.0
        self._task_done_is_cumulative: Optional[bool] = None

    def solve(self, spec_path: str) -> "Solution":
        self._initialized = True
        self._p_spot = 0.5
        self._spot_up_streak = 0
        self._spot_down_streak = 0
        self._done_cache_len = 0
        self._done_cache_sum = 0.0
        self._task_done_is_cumulative = None
        return self

    def _safe_float(self, x: Any) -> Optional[float]:
        try:
            if isinstance(x, bool):
                return None
            return float(x)
        except Exception:
            return None

    def _compute_done_work(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0

        if isinstance(tdt, (int, float)):
            v = float(tdt)
            if v < 0:
                return 0.0
            return min(v, float(self.task_duration))

        if not isinstance(tdt, (list, tuple)):
            return 0.0

        n = len(tdt)
        if n == 0:
            self._done_cache_len = 0
            self._done_cache_sum = 0.0
            return 0.0

        if self._task_done_is_cumulative is None and n >= 6:
            s = 0.0
            ok = True
            for i in range(min(n, 64)):
                v = self._safe_float(tdt[i])
                if v is None:
                    ok = False
                    break
                s += v
            if ok and s > float(self.task_duration) * 1.5:
                self._task_done_is_cumulative = True
            else:
                self._task_done_is_cumulative = False

        if self._task_done_is_cumulative:
            last = self._safe_float(tdt[-1])
            if last is None:
                return 0.0
            if last < 0:
                return 0.0
            return min(last, float(self.task_duration))

        if n < self._done_cache_len:
            self._done_cache_len = 0
            self._done_cache_sum = 0.0

        total = self._done_cache_sum
        for i in range(self._done_cache_len, n):
            item = tdt[i]
            if isinstance(item, (tuple, list)) and len(item) == 2:
                a = self._safe_float(item[0])
                b = self._safe_float(item[1])
                if a is None or b is None:
                    continue
                if b >= a:
                    total += (b - a)
                else:
                    total += b
            else:
                v = self._safe_float(item)
                if v is None:
                    continue
                total += v

        self._done_cache_len = n
        self._done_cache_sum = total

        if total < 0:
            return 0.0
        return min(total, float(self.task_duration))

    def _compute_reserve_slack(self, gap: float, overhead: float) -> float:
        p = min(max(self._p_spot, 1e-6), 1.0 - 1e-9)
        denom = math.log(1.0 - p)
        if denom >= 0:
            outage90_time = 3.0 * 3600.0
        else:
            outage90_steps = math.log(0.1) / denom
            outage90_steps = max(0.0, outage90_steps)
            outage90_time = outage90_steps * gap

        min_finish_slack = overhead + 2.0 * gap
        reserve = 1.2 * outage90_time + overhead + gap
        reserve = max(reserve, 0.5 * 3600.0)
        reserve = min(reserve, 3.0 * 3600.0)
        reserve = max(reserve, min_finish_slack)
        return reserve

    def _required_spot_streak_to_switch(self, gap: float, overhead: float) -> int:
        if gap <= 0:
            return 1
        req = int(math.ceil(overhead / gap)) if overhead > 0 else 1
        req = max(1, min(3, req))
        if self._p_spot < 0.25:
            req = max(req, 2)
        return req

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if has_spot:
            self._spot_up_streak += 1
            self._spot_down_streak = 0
        else:
            self._spot_down_streak += 1
            self._spot_up_streak = 0

        x = 1.0 if has_spot else 0.0
        self._p_spot = (1.0 - self._ema_alpha) * self._p_spot + self._ema_alpha * x

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._compute_done_work()
        remaining_work = float(self.task_duration) - done
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        remaining_time = float(self.deadline) - elapsed
        if remaining_time <= 0:
            return ClusterType.NONE

        min_finish_slack = overhead + 2.0 * gap
        slack = remaining_time - remaining_work

        if remaining_time <= remaining_work + min_finish_slack:
            return ClusterType.ON_DEMAND
        if slack <= min_finish_slack * 1.25:
            return ClusterType.ON_DEMAND

        reserve_slack = self._compute_reserve_slack(gap, overhead)

        if has_spot:
            req_streak = self._required_spot_streak_to_switch(gap, overhead)
            if last_cluster_type == ClusterType.ON_DEMAND and self._spot_up_streak < req_streak:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.NONE and self._spot_up_streak < req_streak:
                if slack <= reserve_slack:
                    return ClusterType.ON_DEMAND
                return ClusterType.NONE
            return ClusterType.SPOT

        if slack > reserve_slack + gap:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)