import json
import math
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = getattr(ClusterType, "SPOT")
_CT_OD = getattr(ClusterType, "ON_DEMAND", getattr(ClusterType, "ONDEMAND"))
_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        self._reset_internal_state()
        return self

    def _reset_internal_state(self) -> None:
        self._inited: bool = False
        self._num_regions: int = 1
        self._region_score: List[float] = []
        self._region_visits: List[int] = []
        self._total_visits: int = 0

        self._done_cached: float = 0.0
        self._task_done_len: int = 0

        self._ema_alpha: float = 0.06
        self._ucb_beta: float = 0.35

    def _ensure_init(self) -> None:
        if self._inited:
            return
        env = self.env
        try:
            self._num_regions = int(env.get_num_regions())
        except Exception:
            self._num_regions = 1

        n = max(1, self._num_regions)
        self._region_score = [0.5] * n
        self._region_visits = [0] * n
        self._total_visits = 0

        self._done_cached = 0.0
        self._task_done_len = 0

        self._inited = True

    def _update_done_cache(self) -> None:
        tdt = self.task_done_time
        if tdt is None:
            return
        n = len(tdt)
        if n <= self._task_done_len:
            return
        new_sum = 0.0
        for i in range(self._task_done_len, n):
            new_sum += float(tdt[i])
        self._done_cached += new_sum
        self._task_done_len = n

    def _update_region_stats(self, region: int, has_spot: bool) -> None:
        if region < 0 or region >= self._num_regions:
            return
        v = self._region_visits[region] + 1
        self._region_visits[region] = v
        self._total_visits += 1
        x = 1.0 if has_spot else 0.0
        s = self._region_score[region]
        a = self._ema_alpha
        self._region_score[region] = s + a * (x - s)

    def _pick_next_region(self, current_region: int) -> int:
        n = self._num_regions
        if n <= 1:
            return current_region

        # Prefer any unvisited region (excluding current).
        for r in range(n):
            if r != current_region and self._region_visits[r] == 0:
                return r

        # UCB on EMA scores.
        log_term = math.log(self._total_visits + 1.0)
        best_r = current_region
        best_ucb = -1e30
        beta = self._ucb_beta
        for r in range(n):
            if r == current_region:
                continue
            v = self._region_visits[r]
            ucb = self._region_score[r] + beta * math.sqrt(log_term / (v + 1.0))
            if ucb > best_ucb:
                best_ucb = ucb
                best_r = r
        return best_r

    def _steps_remaining(self, remaining_time: float, gap: float) -> int:
        if gap <= 0.0:
            return 0
        # Remaining full steps including the upcoming one.
        # Use a tiny epsilon to reduce float boundary issues.
        eps = 1e-9 * max(1.0, abs(remaining_time))
        return int((remaining_time + eps) // gap)

    def _overhead_if_choose(self, chosen: ClusterType, last: ClusterType) -> float:
        if chosen == _CT_NONE:
            return 0.0
        if chosen == last:
            return float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        return float(self.restart_overhead)

    def _work_this_step(self, overhead: float, gap: float) -> float:
        w = gap - overhead
        return w if w > 0.0 else 0.0

    def _feasible_if_choose(
        self,
        chosen: ClusterType,
        last: ClusterType,
        steps_remaining: int,
        remaining_work: float,
        gap: float,
    ) -> bool:
        if remaining_work <= 0.0:
            return True
        if steps_remaining <= 0:
            return False

        if chosen == _CT_NONE:
            work_now = 0.0
            rem_after = remaining_work
            steps_left = steps_remaining - 1
            if rem_after <= 0.0:
                return True
            if steps_left <= 0:
                return False
            overhead_next = float(self.restart_overhead)
            max_future_work = steps_left * gap - overhead_next
            return max_future_work + 1e-9 >= rem_after

        overhead_now = self._overhead_if_choose(chosen, last)
        work_now = self._work_this_step(overhead_now, gap)
        rem_after = remaining_work - work_now
        if rem_after <= 0.0:
            return True

        steps_left = steps_remaining - 1
        if steps_left <= 0:
            return False

        if chosen == _CT_OD:
            overhead_next = overhead_now - gap
            if overhead_next < 0.0:
                overhead_next = 0.0
        else:
            # Worst-case: spot disappears next step -> on-demand restart.
            overhead_next = float(self.restart_overhead)

        max_future_work = steps_left * gap - overhead_next
        return max_future_work + 1e-9 >= rem_after

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        env = self.env
        current_region = 0
        try:
            current_region = int(env.get_current_region())
        except Exception:
            current_region = 0

        self._update_done_cache()
        self._update_region_stats(current_region, bool(has_spot))

        remaining_work = float(self.task_duration) - float(self._done_cached)
        if remaining_work <= 0.0:
            return _CT_NONE

        gap = float(env.gap_seconds)
        remaining_time = float(self.deadline) - float(env.elapsed_seconds)
        steps_remaining = self._steps_remaining(remaining_time, gap)
        if steps_remaining <= 0:
            return _CT_NONE

        # If spot is available, prefer SPOT if it keeps a worst-case completion guarantee.
        if has_spot:
            if self._feasible_if_choose(_CT_SPOT, last_cluster_type, steps_remaining, remaining_work, gap):
                return _CT_SPOT
            return _CT_OD

        # Spot not available:
        # Keep ON_DEMAND running once started to avoid repeated restart overhead from idling.
        if last_cluster_type == _CT_OD:
            return _CT_OD

        # Prefer idling if we can still finish by deadline with on-demand from next step onward.
        if self._feasible_if_choose(_CT_NONE, last_cluster_type, steps_remaining, remaining_work, gap):
            if self._num_regions > 1:
                next_region = self._pick_next_region(current_region)
                if next_region != current_region:
                    try:
                        env.switch_region(int(next_region))
                    except Exception:
                        pass
            return _CT_NONE

        return _CT_OD