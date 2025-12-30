import json
import os
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


class Solution(Strategy):
    NAME = "robust_segment_aware_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args

        self._initialized = False
        self._od_committed = False

        self._overhead_remaining = 0.0  # remaining restart overhead at the START of current step (seconds)

        self._last_has_spot = False
        self._spot_streak = 0.0  # consecutive spot-available time including current step (seconds)
        self._seg_mean = 3600.0  # EWMA mean of spot-available segment length (seconds)
        self._seg_n = 0

        self._od_price = None
        self._spot_price = None
        self._seg_len_threshold = None
        self._explore_until = 3600.0
        self._safety = None

    def solve(self, spec_path: str) -> "Solution":
        self._initialized = True
        self._od_committed = False
        self._overhead_remaining = 0.0
        self._last_has_spot = False
        self._spot_streak = 0.0
        self._seg_mean = 3600.0
        self._seg_n = 0

        self._od_price = None
        self._spot_price = None

        if spec_path and os.path.exists(spec_path):
            data = None
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    txt = f.read()
                try:
                    data = json.loads(txt)
                except Exception:
                    try:
                        import yaml  # type: ignore

                        data = yaml.safe_load(txt)
                    except Exception:
                        data = None
            except Exception:
                data = None

            if isinstance(data, dict):
                for k in ("on_demand_price", "ondemand_price", "od_price", "on_demand", "ondemand"):
                    if k in data and isinstance(data[k], (int, float)):
                        self._od_price = float(data[k])
                        break
                for k in ("spot_price", "spot"):
                    if k in data and isinstance(data[k], (int, float)):
                        self._spot_price = float(data[k])
                        break
                prices = data.get("prices") if isinstance(data.get("prices"), dict) else None
                if prices:
                    if self._od_price is None:
                        for k in ("on_demand", "ondemand", "od"):
                            if k in prices and isinstance(prices[k], (int, float)):
                                self._od_price = float(prices[k])
                                break
                    if self._spot_price is None:
                        for k in ("spot",):
                            if k in prices and isinstance(prices[k], (int, float)):
                                self._spot_price = float(prices[k])
                                break

        self._seg_len_threshold = None
        self._safety = None
        self._explore_until = 3600.0
        return self

    @staticmethod
    def _sum_task_done(task_done_time: Any, task_duration: float) -> float:
        if task_done_time is None:
            return 0.0
        if isinstance(task_done_time, (int, float)):
            return float(task_done_time)

        if isinstance(task_done_time, (list, tuple)):
            if not task_done_time:
                return 0.0

            if all(isinstance(x, (int, float)) for x in task_done_time):
                arr = [float(x) for x in task_done_time]
                monotonic = True
                for i in range(len(arr) - 1):
                    if arr[i] > arr[i + 1]:
                        monotonic = False
                        break
                s = float(sum(arr))
                last = float(arr[-1])
                if monotonic and last <= task_duration * 1.05:
                    if s > last * 1.5:
                        return s
                    return last
                return s

            tot = 0.0
            for x in task_done_time:
                if isinstance(x, (int, float)):
                    tot += float(x)
                elif isinstance(x, dict):
                    used = False
                    for key in ("duration", "seconds", "done", "work"):
                        v = x.get(key)
                        if isinstance(v, (int, float)):
                            tot += float(v)
                            used = True
                            break
                    if not used:
                        s = x.get("start")
                        e = x.get("end")
                        if isinstance(s, (int, float)) and isinstance(e, (int, float)):
                            tot += float(e) - float(s)
                elif isinstance(x, (tuple, list)) and len(x) >= 2:
                    a, b = x[0], x[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        tot += float(b) - float(a)
            if tot > 0.0:
                return tot

        try:
            return float(task_done_time)
        except Exception:
            return 0.0

    def _ensure_params(self):
        if self._seg_len_threshold is None:
            o = _safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
            if self._od_price is not None and self._spot_price is not None and self._od_price > self._spot_price:
                ratio = self._od_price / (self._od_price - self._spot_price)
                self._seg_len_threshold = max(0.0, ratio * o)
            else:
                self._seg_len_threshold = 1.5 * o

        if self._safety is None:
            gap = _safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
            o = _safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
            self._safety = max(0.0, 2.0 * gap + 0.75 * o + 60.0)

        if self._explore_until is None:
            self._explore_until = 3600.0

    def _update_spot_segment_stats(self, has_spot: bool, gap: float):
        if self._last_has_spot and not has_spot:
            L = float(self._spot_streak)
            if L > 0.0:
                self._seg_n += 1
                beta = 0.15
                if self._seg_n <= 3:
                    beta = 0.35
                self._seg_mean = (1.0 - beta) * self._seg_mean + beta * L

        if has_spot:
            if self._last_has_spot:
                self._spot_streak += gap
            else:
                self._spot_streak = gap
        else:
            self._spot_streak = 0.0

        self._last_has_spot = bool(has_spot)

    def _effective_last_cluster(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            return ClusterType.NONE
        return last_cluster_type

    def _compute_overhead_start_for_choice(
        self,
        choice: ClusterType,
        effective_last: ClusterType,
    ) -> float:
        if choice == ClusterType.NONE:
            return 0.0
        if choice != effective_last:
            return _safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        return float(self._overhead_remaining)

    def _is_safe_if_commit_od_next_step(
        self,
        remaining_work_after_this_step: float,
        time_left_next: float,
        safety: float,
    ) -> bool:
        o = _safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        return (time_left_next - safety) >= (remaining_work_after_this_step + o)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_params()

        elapsed = _safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        gap = _safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        deadline = _safe_float(getattr(self, "deadline", 0.0), 0.0)
        task_duration = _safe_float(getattr(self, "task_duration", 0.0), 0.0)
        safety = float(self._safety)

        if gap <= 0.0:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        self._update_spot_segment_stats(bool(has_spot), gap)

        if last_cluster_type in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            self._overhead_remaining = max(0.0, float(self._overhead_remaining) - gap)
        else:
            self._overhead_remaining = 0.0

        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self._overhead_remaining = 0.0

        done = self._sum_task_done(getattr(self, "task_done_time", None), task_duration)
        remaining = max(0.0, task_duration - done)

        if remaining <= 0.0:
            self._overhead_remaining = 0.0
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)
        time_left_next = time_left - gap

        if self._od_committed:
            if has_spot is False and last_cluster_type == ClusterType.SPOT:
                pass
            effective_last = self._effective_last_cluster(last_cluster_type, has_spot)
            oh_start = self._compute_overhead_start_for_choice(ClusterType.ON_DEMAND, effective_last)
            self._overhead_remaining = oh_start
            return ClusterType.ON_DEMAND

        effective_last = self._effective_last_cluster(last_cluster_type, has_spot)

        if not has_spot:
            if time_left_next >= 0.0 and self._is_safe_if_commit_od_next_step(remaining, time_left_next, safety):
                self._overhead_remaining = 0.0
                return ClusterType.NONE
            self._od_committed = True
            oh_start = self._compute_overhead_start_for_choice(ClusterType.ON_DEMAND, effective_last)
            self._overhead_remaining = oh_start
            return ClusterType.ON_DEMAND

        expected_seg_len = max(float(self._seg_mean), float(self._spot_streak))
        want_spot = (effective_last == ClusterType.SPOT) or (elapsed <= float(self._explore_until)) or (
            expected_seg_len >= float(self._seg_len_threshold)
        )

        if want_spot:
            oh_spot = self._compute_overhead_start_for_choice(ClusterType.SPOT, effective_last)
            work_spot = max(0.0, gap - oh_spot)
            remaining_after = max(0.0, remaining - work_spot)

            if time_left_next >= 0.0 and self._is_safe_if_commit_od_next_step(remaining_after, time_left_next, safety):
                self._overhead_remaining = oh_spot
                return ClusterType.SPOT

        if time_left_next >= 0.0 and self._is_safe_if_commit_od_next_step(remaining, time_left_next, safety):
            self._overhead_remaining = 0.0
            return ClusterType.NONE

        self._od_committed = True
        oh_od = self._compute_overhead_start_for_choice(ClusterType.ON_DEMAND, effective_last)
        self._overhead_remaining = oh_od
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)