import math
from typing import Any, Iterable, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self._params_ready = False
        self._units_mult = 1.0

        self._safety_buffer = 600.0
        self._reserve_slack = 3600.0
        self._final_od_window = 1800.0
        self._min_od_lock = 1800.0
        self._switch_back_min_remaining = 7200.0
        self._spot_stable_required = 1

        self._od_lock_until = 0.0
        self._spot_stable = 0
        self._total_steps = 0
        self._spot_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _safe_sum_task_done(task_done_time: Any) -> float:
        if task_done_time is None:
            return 0.0
        if isinstance(task_done_time, (int, float)):
            return float(task_done_time)
        if isinstance(task_done_time, dict):
            v = task_done_time.get("duration") or task_done_time.get("done") or 0.0
            try:
                return float(v)
            except Exception:
                return 0.0
        if isinstance(task_done_time, (list, tuple)):
            total = 0.0
            for x in task_done_time:
                if x is None:
                    continue
                if isinstance(x, (int, float)):
                    total += float(x)
                elif isinstance(x, dict):
                    v = x.get("duration") or x.get("done") or 0.0
                    try:
                        total += float(v)
                    except Exception:
                        pass
                elif isinstance(x, (list, tuple)) and len(x) >= 2:
                    a, b = x[0], x[1]
                    try:
                        total += float(b) - float(a)
                    except Exception:
                        pass
                else:
                    try:
                        total += float(x)
                    except Exception:
                        pass
            return total
        try:
            return float(task_done_time)
        except Exception:
            return 0.0

    def _ensure_params(self) -> None:
        if self._params_ready:
            return

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if deadline > 0 and deadline < 10000 and task_duration > 0 and task_duration < 10000:
            self._units_mult = 3600.0
        else:
            self._units_mult = 1.0

        total_slack = max(0.0, deadline - task_duration) * self._units_mult
        restart = restart_overhead * self._units_mult

        self._safety_buffer = max(600.0, 2.0 * restart, 2.0 * gap)
        self._reserve_slack = max(3600.0, 0.25 * total_slack, 4.0 * restart)
        self._final_od_window = max(1800.0, 0.125 * total_slack, 10.0 * restart)
        self._min_od_lock = max(1800.0, 0.20 * total_slack, 15.0 * restart, 5.0 * gap)
        self._switch_back_min_remaining = max(7200.0, 0.15 * (task_duration * self._units_mult))
        self._spot_stable_required = max(1, int(math.ceil(900.0 / max(gap, 1e-6))))

        self._params_ready = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_params()

        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1
            self._spot_stable += 1
        else:
            self._spot_stable = 0

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)

        deadline = float(getattr(self, "deadline", 0.0) or 0.0) * self._units_mult
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0) * self._units_mult
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0) * self._units_mult
        done = self._safe_sum_task_done(getattr(self, "task_done_time", None)) * self._units_mult

        remaining_work = max(0.0, task_duration - done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work

        od_start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        force_od = False
        if time_left <= self._final_od_window:
            force_od = True
        if time_left <= remaining_work + od_start_overhead + self._safety_buffer:
            force_od = True

        if force_od:
            self._od_lock_until = max(self._od_lock_until, deadline)
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND and elapsed < self._od_lock_until:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            if has_spot:
                if elapsed >= self._od_lock_until:
                    if (
                        self._spot_stable >= self._spot_stable_required
                        and remaining_work >= self._switch_back_min_remaining
                        and slack >= (self._reserve_slack + restart_overhead + self._safety_buffer)
                        and time_left >= (remaining_work + 2.0 * restart_overhead + 2.0 * self._safety_buffer)
                    ):
                        return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if slack > (self._reserve_slack + self._safety_buffer):
            return ClusterType.NONE

        self._od_lock_until = max(self._od_lock_until, elapsed + self._min_od_lock)
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
