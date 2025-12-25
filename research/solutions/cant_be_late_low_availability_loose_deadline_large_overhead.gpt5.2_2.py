import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._ema_p: float = 0.2
        self._ema_alpha: float = 0.03

        self._panic: bool = False

        self._lock_type: Optional[ClusterType] = None
        self._lock_until: float = 0.0

        self._od_started_at: Optional[float] = None

        self._tdt_id: Optional[int] = None
        self._tdt_len: int = 0
        self._tdt_sum: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _parse_done_elem(self, x: Any) -> float:
        if isinstance(x, (int, float)):
            v = float(x)
            if v > 0:
                return v
            return 0.0
        if isinstance(x, (list, tuple)):
            if len(x) == 0:
                return 0.0
            if len(x) == 1 and isinstance(x[0], (int, float)):
                v = float(x[0])
                return v if v > 0 else 0.0
            if len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                a = float(x[0])
                b = float(x[1])
                if b >= a:
                    return max(0.0, b - a)
                return 0.0
            return 0.0
        if isinstance(x, dict):
            if "duration" in x and isinstance(x["duration"], (int, float)):
                v = float(x["duration"])
                return v if v > 0 else 0.0
            if "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(x["end"], (int, float)):
                a = float(x["start"])
                b = float(x["end"])
                if b >= a:
                    return max(0.0, b - a)
            return 0.0
        return 0.0

    def _done_work_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return max(0.0, float(td))
        if isinstance(td, (list, tuple)):
            if not td:
                self._tdt_id = id(td)
                self._tdt_len = 0
                self._tdt_sum = 0.0
                return 0.0
            if id(td) == self._tdt_id and len(td) >= self._tdt_len:
                s = self._tdt_sum
                for i in range(self._tdt_len, len(td)):
                    s += self._parse_done_elem(td[i])
                self._tdt_sum = s
                self._tdt_len = len(td)
                return s
            s = 0.0
            for x in td:
                s += self._parse_done_elem(x)
            self._tdt_id = id(td)
            self._tdt_len = len(td)
            self._tdt_sum = s
            return s
        return 0.0

    def _set_lock(self, ctype: ClusterType, elapsed: float, gap: float) -> None:
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if ro <= 0.0:
            self._lock_type = None
            self._lock_until = 0.0
            return
        if gap <= 0.0:
            gap = 1.0
        if ro <= 0.75 * gap:
            self._lock_type = None
            self._lock_until = 0.0
            return
        self._lock_type = ctype
        self._lock_until = elapsed + ro

    def _buffer_seconds(self, gap: float) -> float:
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        return max(2.0 * gap, 600.0, 0.25 * ro)

    def _od_min_seconds(self, gap: float) -> float:
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        return max(3600.0, 3.0 * ro, 6.0 * gap)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 300.0) or 300.0)
        if gap <= 0.0:
            gap = 1.0

        obs = 1.0 if has_spot else 0.0
        self._ema_p = (1.0 - self._ema_alpha) * self._ema_p + self._ema_alpha * obs

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)

        done = self._done_work_seconds()
        remaining_work = max(0.0, task_duration - done)
        if remaining_work <= 0.0:
            self._panic = False
            self._lock_type = None
            self._lock_until = 0.0
            self._od_started_at = None
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            self._panic = True

        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        buffer_base = self._buffer_seconds(gap)
        od_start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else ro
        required_if_od_now = remaining_work + od_start_overhead + buffer_base

        if remaining_time <= required_if_od_now:
            self._panic = True

        if self._panic:
            action = ClusterType.ON_DEMAND
            if self._od_started_at is None:
                self._od_started_at = elapsed
            if action != last_cluster_type:
                self._set_lock(action, elapsed, gap)
            return action

        if self._lock_type is not None and elapsed < self._lock_until:
            if self._lock_type == ClusterType.SPOT and not has_spot:
                self._lock_type = None
                self._lock_until = 0.0
            else:
                if self._lock_type == ClusterType.SPOT and not has_spot:
                    return ClusterType.ON_DEMAND
                return self._lock_type

        slack = remaining_time - required_if_od_now

        if last_cluster_type == ClusterType.ON_DEMAND:
            if self._od_started_at is None:
                self._od_started_at = elapsed
            if has_spot:
                can_switch = (
                    (elapsed - self._od_started_at) >= self._od_min_seconds(gap)
                    and slack > (ro + 3.0 * gap)
                    and self._ema_p > 0.12
                )
                action = ClusterType.SPOT if can_switch else ClusterType.ON_DEMAND
            else:
                action = ClusterType.ON_DEMAND
        else:
            self._od_started_at = None
            if has_spot:
                action = ClusterType.SPOT
                if last_cluster_type != ClusterType.SPOT and slack < (ro + 2.0 * gap):
                    action = ClusterType.ON_DEMAND
            else:
                p = max(self._ema_p, 0.01)
                expected_wait = (1.0 - p) / p * gap
                margin = ro + 2.0 * gap
                if slack > expected_wait + margin:
                    action = ClusterType.NONE
                else:
                    action = ClusterType.ON_DEMAND

        if action == ClusterType.SPOT and not has_spot:
            action = ClusterType.ON_DEMAND if remaining_time <= required_if_od_now + gap else ClusterType.NONE

        if action != last_cluster_type and action in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            self._set_lock(action, elapsed, gap)

        if action == ClusterType.ON_DEMAND and self._od_started_at is None:
            self._od_started_at = elapsed

        return action

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)