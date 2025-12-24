import json
import math
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

    _P_ON_DEMAND = 3.06
    _P_SPOT = 0.9701

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

        self._inited = False
        self._region_n: List[int] = []
        self._region_alpha: List[float] = []
        self._region_beta: List[float] = []
        self._total_obs: int = 0

        self._last_td_len: int = 0
        self._progress: float = 0.0

        self._ucb_c: float = 0.55
        return self

    @staticmethod
    def _ct_none() -> ClusterType:
        ct = getattr(ClusterType, "NONE", None)
        if ct is not None:
            return ct
        return getattr(ClusterType, "None")

    def _lazy_init(self) -> None:
        if self._inited:
            return
        n = int(self.env.get_num_regions())
        if n <= 0:
            n = 1
        self._region_n = [0] * n
        self._region_alpha = [1.0] * n
        self._region_beta = [1.0] * n
        self._total_obs = 0

        td = getattr(self, "task_done_time", None)
        if td:
            self._progress = float(sum(td))
            self._last_td_len = len(td)
        else:
            self._progress = 0.0
            self._last_td_len = 0

        self._inited = True

    def _update_progress(self) -> None:
        td = self.task_done_time
        if td is None:
            return
        cur_len = len(td)
        if cur_len == self._last_td_len:
            return
        if cur_len > self._last_td_len:
            self._progress += float(sum(td[self._last_td_len : cur_len]))
            self._last_td_len = cur_len
        else:
            self._progress = float(sum(td))
            self._last_td_len = cur_len

    def _observe_region(self, region: int, has_spot: bool) -> None:
        if region < 0 or region >= len(self._region_n):
            return
        self._total_obs += 1
        self._region_n[region] += 1
        if has_spot:
            self._region_alpha[region] += 1.0
        else:
            self._region_beta[region] += 1.0

    def _choose_region_ucb(self, exclude: Optional[int] = None) -> int:
        n = len(self._region_n)
        if n <= 1:
            return 0
        total = max(1, self._total_obs)
        log_total = math.log(total + 1.0)

        best_idx = 0
        best_score = -1e30
        for i in range(n):
            if exclude is not None and i == exclude:
                continue
            ni = self._region_n[i]
            if ni <= 0:
                score = 2.0
            else:
                mean = self._region_alpha[i] / (self._region_alpha[i] + self._region_beta[i])
                bonus = self._ucb_c * math.sqrt(log_total / ni)
                score = mean + bonus
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _steps_left(self, elapsed: float) -> int:
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return 0
        time_left = float(self.deadline) - float(elapsed)
        if time_left <= 0:
            return 0
        return int(math.floor((time_left + 1e-9) / gap))

    def _overhead_to_pay(self, action: ClusterType, last_cluster_type: ClusterType) -> float:
        if action == self._ct_none():
            return 0.0
        if action == last_cluster_type:
            try:
                return float(self.remaining_restart_overhead)
            except Exception:
                return 0.0
        return float(self.restart_overhead)

    def _work_this_step_lb(self, action: ClusterType, last_cluster_type: ClusterType) -> float:
        if action == self._ct_none():
            return 0.0
        gap = float(self.env.gap_seconds)
        oh = self._overhead_to_pay(action, last_cluster_type)
        w = gap - oh
        return w if w > 0.0 else 0.0

    def _capacity_if_od_from_next(self, steps_left_after: int, initial_overhead: float) -> float:
        if steps_left_after <= 0:
            return 0.0
        gap = float(self.env.gap_seconds)
        cap = steps_left_after * gap - float(initial_overhead)
        return cap if cap > 0.0 else 0.0

    def _switch_od_to_spot_is_worthwhile(self) -> bool:
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return False
        save = (self._P_ON_DEMAND - self._P_SPOT) * (gap / 3600.0)
        overhead_cost = self._P_ON_DEMAND * (float(self.restart_overhead) / 3600.0)
        return save > overhead_cost + 1e-12

    def _spot_feasible_and_preferred(self, last_cluster_type: ClusterType, has_spot: bool, steps_left: int, remaining_work: float) -> bool:
        if not has_spot:
            return False
        if steps_left <= 0:
            return False

        if last_cluster_type == ClusterType.ON_DEMAND and not self._switch_od_to_spot_is_worthwhile():
            return False

        work_now = self._work_this_step_lb(ClusterType.SPOT, last_cluster_type)
        rem_after = remaining_work - work_now
        if rem_after <= 1e-9:
            return True

        steps_after = steps_left - 1
        cap_future = self._capacity_if_od_from_next(steps_after, float(self.restart_overhead))
        return rem_after <= cap_future + 1e-6

    def _none_feasible(self, steps_left: int, remaining_work: float) -> bool:
        if steps_left <= 0:
            return remaining_work <= 1e-9
        steps_after = steps_left - 1
        cap_future = self._capacity_if_od_from_next(steps_after, float(self.restart_overhead))
        return remaining_work <= cap_future + 1e-6

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_progress()

        ct_none = self._ct_none()

        try:
            task_duration = float(self.task_duration)
        except Exception:
            td = getattr(self, "task_duration", 0.0)
            if isinstance(td, (list, tuple)) and td:
                task_duration = float(td[0])
            else:
                task_duration = float(td) if td is not None else 0.0

        remaining_work = task_duration - float(self._progress)
        if remaining_work <= 1e-9:
            return ct_none

        elapsed = float(self.env.elapsed_seconds)
        steps_left = self._steps_left(elapsed)
        if steps_left <= 0:
            return ct_none

        cur_region = int(self.env.get_current_region())
        self._observe_region(cur_region, bool(has_spot))

        if self._spot_feasible_and_preferred(last_cluster_type, bool(has_spot), steps_left, remaining_work):
            return ClusterType.SPOT

        if not bool(has_spot) and self._none_feasible(steps_left, remaining_work):
            if self.env.get_num_regions() > 1:
                next_region = self._choose_region_ucb(exclude=cur_region)
                if next_region != cur_region:
                    self.env.switch_region(next_region)
            return ct_none

        return ClusterType.ON_DEMAND
