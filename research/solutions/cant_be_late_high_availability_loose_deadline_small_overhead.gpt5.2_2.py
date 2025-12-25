import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            super().__init__()
        self._commit_od = False
        self._od_lock_until = 0.0
        self._prev_has_spot = None
        self._ema_spot_avail = 0.7

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _estimate_done_work(self) -> float:
        t = getattr(self, "task_done_time", None)
        if t is None:
            return 0.0
        if isinstance(t, (int, float)):
            return float(t)
        if not isinstance(t, (list, tuple)) or len(t) == 0:
            return 0.0

        vals = []
        for x in t:
            if isinstance(x, (int, float)):
                vals.append(float(x))
            elif isinstance(x, (list, tuple)) and x:
                y = x[-1]
                if isinstance(y, (int, float)):
                    vals.append(float(y))

        if not vals:
            return 0.0
        if len(vals) == 1:
            return max(0.0, vals[0])

        s = sum(vals)
        mx = max(vals)
        nondec = True
        for i in range(1, len(vals)):
            if vals[i] + 1e-9 < vals[i - 1]:
                nondec = False
                break

        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        # Heuristic: if values look cumulative and bounded by task duration, use max; else sum.
        if task_dur > 0.0 and nondec and mx <= 1.1 * task_dur and mx >= 0.45 * s:
            return max(0.0, mx)
        return max(0.0, s)

    def _remaining_work(self) -> float:
        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = self._estimate_done_work()
        return max(0.0, task_dur - done)

    def _update_ema(self, has_spot: bool) -> None:
        alpha = 0.02
        x = 1.0 if has_spot else 0.0
        self._ema_spot_avail = alpha * x + (1.0 - alpha) * self._ema_spot_avail
        self._prev_has_spot = has_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_ema(has_spot)

        dt = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            return ClusterType.NONE

        slack = remaining_time - remaining_work

        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        wait_reserve = max(3600.0, 20.0 * ro, 4.0 * dt)        # ~1h+
        final_reserve = max(5400.0, 30.0 * ro, 6.0 * dt)       # ~1.5h+

        if (slack <= final_reserve) or (remaining_time <= remaining_work + final_reserve):
            self._commit_od = True

        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Avoid rapid thrashing if we recently decided to stay on OD for stability.
        if last_cluster_type == ClusterType.ON_DEMAND and elapsed < self._od_lock_until:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # No spot available: wait if we still have enough slack budget, otherwise use OD.
        if slack > wait_reserve:
            # If we are already on OD (unlikely here due to lock/commit), keep OD rather than stopping.
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE

        # Use OD and set a short lock to avoid OD<->SPOT flapping.
        self._od_lock_until = max(self._od_lock_until, elapsed + 6.0 * dt)
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)