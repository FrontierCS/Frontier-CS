import math
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # Fallback stubs for non-eval environments
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:
        def __init__(self, args: Any = None):
            self.env = type("Env", (), {"elapsed_seconds": 0.0, "gap_seconds": 300.0, "cluster_type": ClusterType.NONE})()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            super().__init__()

        self._args = args

        self._obs_total = 0
        self._obs_spot = 0

        self._od_accum_unavail = 0.0
        self._od_accum_avail = 0.0

        self._od_lock_steps = 0
        self._min_od_chunk_steps = 1

        self._cached_gap = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_done_work_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0
        total = 0.0
        try:
            for x in tdt:
                if x is None:
                    continue
                if isinstance(x, (int, float)):
                    total += float(x)
                elif isinstance(x, (tuple, list)):
                    if len(x) == 0:
                        continue
                    if len(x) == 1:
                        v = x[0]
                        if isinstance(v, (int, float)):
                            total += float(v)
                    else:
                        a = x[0]
                        b = x[1]
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                            if b >= a:
                                total += float(b - a)
                            else:
                                total += float(b)
                elif isinstance(x, dict):
                    if "duration" in x and isinstance(x["duration"], (int, float)):
                        total += float(x["duration"])
                    elif "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(x["end"], (int, float)):
                        if x["end"] >= x["start"]:
                            total += float(x["end"] - x["start"])
        except Exception:
            return 0.0
        return max(0.0, total)

    def _update_chunk_params(self) -> None:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 60.0
        self._cached_gap = gap
        oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        self._min_od_chunk_steps = max(1, int(math.ceil(oh / gap)) + 1)

    def _apply_od_lock(self, desired: ClusterType, last_cluster_type: ClusterType) -> ClusterType:
        if self._od_lock_steps > 0:
            self._od_lock_steps -= 1
            return ClusterType.ON_DEMAND

        if desired == ClusterType.ON_DEMAND and last_cluster_type != ClusterType.ON_DEMAND:
            self._od_lock_steps = self._min_od_chunk_steps - 1
            return ClusterType.ON_DEMAND

        return desired

    def _posterior_availability(self) -> tuple[float, float]:
        alpha = 1.0
        beta = 5.0
        n = self._obs_total
        s = self._obs_spot
        denom = n + alpha + beta
        p_hat = (s + alpha) / denom if denom > 0 else alpha / (alpha + beta)
        p_hat = min(0.999, max(0.001, p_hat))

        n_eff = denom
        std = math.sqrt(max(1e-12, p_hat * (1.0 - p_hat) / max(1.0, n_eff)))
        k = 1.8
        p_cons = p_hat - k * std
        p_cons = min(0.98, max(0.01, p_cons))
        return p_hat, p_cons

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self._cached_gap is None:
            self._update_chunk_params()

        self._obs_total += 1
        if has_spot:
            self._obs_spot += 1

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", self._cached_gap) or self._cached_gap or 60.0)
        if gap <= 0:
            gap = 60.0
        self._cached_gap = gap

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._get_done_work_seconds()
        remaining_work = max(0.0, task_duration - done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        safety_buffer = max(oh * 4.0, gap * 1.5)
        hard_buffer = max(oh * 8.0, gap * 2.0)

        slack = time_left - remaining_work

        if time_left <= remaining_work + hard_buffer or slack <= 0.0:
            desired = ClusterType.ON_DEMAND
            return self._apply_od_lock(desired, last_cluster_type)

        p_hat, p_cons = self._posterior_availability()

        od_need = max(0.0, remaining_work - p_cons * time_left)
        if od_need <= 0.0:
            if has_spot:
                desired = ClusterType.SPOT
            else:
                if slack >= (gap + safety_buffer):
                    desired = ClusterType.NONE
                else:
                    desired = ClusterType.ON_DEMAND
            if desired == ClusterType.SPOT and not has_spot:
                desired = ClusterType.NONE
            return self._apply_od_lock(desired, last_cluster_type)

        unavail_cons = max(0.0, (1.0 - p_cons) * time_left)
        if slack <= safety_buffer:
            desired = ClusterType.ON_DEMAND
            return self._apply_od_lock(desired, last_cluster_type)

        if not has_spot:
            if unavail_cons <= 1e-9:
                desired = ClusterType.ON_DEMAND
                return self._apply_od_lock(desired, last_cluster_type)

            rate = od_need / unavail_cons
            rate = min(1.0, max(0.0, rate))

            urgency = 1.0 - min(1.0, max(0.0, slack / max(1e-9, 6.0 * safety_buffer)))
            rate = min(1.0, rate * (1.0 + 0.75 * urgency))

            self._od_accum_unavail += rate
            if self._od_accum_unavail >= 1.0:
                self._od_accum_unavail -= 1.0
                desired = ClusterType.ON_DEMAND
            else:
                desired = ClusterType.NONE
                if slack < (gap + safety_buffer * 0.25):
                    desired = ClusterType.ON_DEMAND

            return self._apply_od_lock(desired, last_cluster_type)

        extra_od = od_need - unavail_cons
        if extra_od <= 0.0:
            desired = ClusterType.SPOT
            if desired == ClusterType.SPOT and not has_spot:
                desired = ClusterType.NONE
            return self._apply_od_lock(desired, last_cluster_type)

        denom = max(1e-9, p_cons * time_left)
        rate_a = extra_od / denom
        rate_a = min(1.0, max(0.0, rate_a))

        urgency = 1.0 - min(1.0, max(0.0, slack / max(1e-9, 6.0 * safety_buffer)))
        rate_a = min(1.0, rate_a * (1.0 + 0.75 * urgency))

        self._od_accum_avail += rate_a
        if self._od_accum_avail >= 1.0:
            self._od_accum_avail -= 1.0
            desired = ClusterType.ON_DEMAND
        else:
            desired = ClusterType.SPOT

        if desired == ClusterType.SPOT and not has_spot:
            desired = ClusterType.NONE

        return self._apply_od_lock(desired, last_cluster_type)

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
