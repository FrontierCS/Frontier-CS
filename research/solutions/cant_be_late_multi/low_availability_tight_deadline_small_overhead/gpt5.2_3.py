import json
import math
from argparse import Namespace
from typing import Optional, List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_safe_ucb"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._done_work_seconds: float = 0.0
        self._task_done_len: int = 0

        self._num_regions: Optional[int] = None
        self._avail_ema: Optional[List[float]] = None
        self._avail_cnt: Optional[List[int]] = None
        self._avail_total: int = 0

        return self

    def _update_done_work(self) -> None:
        td = self.task_done_time
        l = len(td)
        if l > self._task_done_len:
            self._done_work_seconds += sum(td[self._task_done_len:l])
            self._task_done_len = l

    def _ensure_region_stats(self) -> None:
        if self._num_regions is not None:
            return
        n = int(self.env.get_num_regions())
        self._num_regions = n
        self._avail_ema = [0.5] * n
        self._avail_cnt = [0] * n
        self._avail_total = 0

    def _update_region_stats(self, region: int, has_spot: bool) -> None:
        self._ensure_region_stats()
        assert self._avail_ema is not None and self._avail_cnt is not None
        alpha = 0.07
        x = 1.0 if has_spot else 0.0
        self._avail_ema[region] = (1.0 - alpha) * self._avail_ema[region] + alpha * x
        self._avail_cnt[region] += 1
        self._avail_total += 1

    def _best_region_ucb(self, current_region: int) -> int:
        assert self._num_regions is not None
        assert self._avail_ema is not None and self._avail_cnt is not None
        n = self._num_regions
        if n <= 1:
            return current_region

        total = max(1, self._avail_total)
        logt = math.log(total + 1.0)
        explore = 0.25

        best_i = current_region
        best_score = -1e18
        for i in range(n):
            cnt = self._avail_cnt[i]
            bonus = explore * math.sqrt(logt / (cnt + 1.0))
            score = self._avail_ema[i] + bonus
            if score > best_score + 1e-12:
                best_score = score
                best_i = i
        return best_i

    def _feasible_after_action(
        self,
        choice: ClusterType,
        last_cluster_type: ClusterType,
        remaining_work: float,
        elapsed: float,
    ) -> bool:
        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        H = float(self.restart_overhead)

        if remaining_work <= 1e-9:
            return True

        if choice == ClusterType.NONE:
            work_gain = 0.0
            rem_over_after = 0.0
            future_overhead = H
        else:
            if choice != last_cluster_type:
                step_over = H
            else:
                step_over = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

            if step_over >= gap:
                work_gain = 0.0
                rem_over_after = step_over - gap
            else:
                work_gain = gap - step_over
                rem_over_after = 0.0

            if choice == ClusterType.ON_DEMAND:
                future_overhead = rem_over_after
            else:
                future_overhead = H

        rem_after = remaining_work - work_gain
        if rem_after <= 1e-9:
            return True

        t_after = elapsed + gap
        time_left_after = deadline - t_after
        if time_left_after < -1e-9:
            return False

        needed = future_overhead + rem_after
        return time_left_after + 1e-9 >= needed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_region_stats()

        self._update_done_work()
        elapsed = float(self.env.elapsed_seconds)
        remaining_work = float(self.task_duration) - float(self._done_work_seconds)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        current_region = int(self.env.get_current_region())
        self._update_region_stats(current_region, bool(has_spot))

        # Prefer cheapest feasible option while guaranteeing that we can always
        # finish by switching to on-demand from the next step onward.
        if has_spot:
            if self._feasible_after_action(ClusterType.SPOT, last_cluster_type, remaining_work, elapsed):
                return ClusterType.SPOT

        if self._feasible_after_action(ClusterType.NONE, last_cluster_type, remaining_work, elapsed):
            # While pausing, opportunistically move to a region that seems more likely to have spot.
            # Avoid switching if a restart overhead is currently pending, to not accidentally reset it.
            rem_ov = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
            if rem_ov <= 1e-9 and self._num_regions is not None and self._num_regions > 1:
                best = self._best_region_ucb(current_region)
                if best != current_region:
                    self.env.switch_region(best)
            return ClusterType.NONE

        return ClusterType.ON_DEMAND