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
            except TypeError:
                pass

        self._reserve_seconds: Optional[float] = None
        self._switch_back_buffer_seconds: Optional[float] = None
        self._epsilon = 1e-9
        self._lock_on_demand = False

        self._seen_steps = 0
        self._seen_spot_available_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0
        total = 0.0
        for seg in tdt:
            if seg is None:
                continue
            if isinstance(seg, (int, float)):
                total += float(seg)
                continue
            if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                a = seg[0]
                b = seg[1]
                try:
                    fa = float(a)
                    fb = float(b)
                    if fb >= fa:
                        total += fb - fa
                    else:
                        total += fa
                except Exception:
                    try:
                        total += float(seg[0])
                    except Exception:
                        pass
                continue
            try:
                total += float(seg)
            except Exception:
                pass
        return total

    def _init_thresholds_if_needed(self) -> None:
        if self._reserve_seconds is not None and self._switch_back_buffer_seconds is not None:
            return
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        self._reserve_seconds = max(600.0, 4.0 * gap, 4.0 * overhead)
        self._switch_back_buffer_seconds = max(1800.0, 12.0 * gap, 12.0 * overhead)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_thresholds_if_needed()

        self._seen_steps += 1
        if has_spot:
            self._seen_spot_available_steps += 1

        if last_cluster_type is None:
            last_cluster_type = ClusterType.NONE

        done = self._compute_done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(0.0, task_duration - done)

        if remaining_work <= self._epsilon:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_time = max(0.0, deadline - elapsed)

        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        reserve = float(self._reserve_seconds or 0.0)
        switch_back_buf = float(self._switch_back_buffer_seconds or 0.0)

        if self._lock_on_demand:
            return ClusterType.ON_DEMAND

        overhead_to_start_od_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead
        slack_if_od_now = remaining_time - (remaining_work + overhead_to_start_od_now)

        if slack_if_od_now <= self._epsilon:
            self._lock_on_demand = True
            return ClusterType.ON_DEMAND

        if slack_if_od_now <= reserve:
            self._lock_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            overhead_to_start_spot_now = 0.0 if last_cluster_type == ClusterType.SPOT else overhead
            if slack_if_od_now <= reserve + overhead_to_start_spot_now:
                return ClusterType.ON_DEMAND

            if last_cluster_type == ClusterType.ON_DEMAND and slack_if_od_now < (reserve + switch_back_buf):
                return ClusterType.ON_DEMAND

            return ClusterType.SPOT

        # No spot available: decide between waiting and on-demand.
        # If we wait one step, we must still be able to finish by starting OD next step (paying restart overhead).
        can_idle_one_step = (remaining_time - gap) >= (remaining_work + overhead + reserve)
        if can_idle_one_step:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)