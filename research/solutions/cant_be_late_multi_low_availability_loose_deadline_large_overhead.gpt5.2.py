import json
import math
from argparse import Namespace
from typing import Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_bandit_v1"

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

        self._initialized = False
        self._locked_ondemand = False

        return self

    def _lazy_init(self) -> None:
        if self._initialized:
            return

        self._CT_SPOT = getattr(ClusterType, "SPOT")
        self._CT_ON_DEMAND = getattr(ClusterType, "ON_DEMAND")
        self._CT_NONE = getattr(ClusterType, "NONE", None)
        if self._CT_NONE is None:
            self._CT_NONE = getattr(ClusterType, "None")

        n = int(self.env.get_num_regions())
        self._n_regions = n
        self._spot_count = [0] * n
        self._total_count = [0] * n
        self._total_obs = 0

        self._consec_no_spot = 0
        self._last_switch_elapsed = float("-inf")

        self._work_done = 0.0
        self._last_task_done_len = 0

        self._ucb_c = 0.80

        self._initialized = True

    def _sync_work_done(self) -> None:
        td = self.task_done_time
        if td is None:
            return
        l = len(td)
        if l < self._last_task_done_len:
            self._work_done = float(sum(td))
            self._last_task_done_len = l
            return
        if l > self._last_task_done_len:
            self._work_done += float(sum(td[self._last_task_done_len :]))
            self._last_task_done_len = l

    def _region_scores(self) -> Tuple[list, list]:
        t = float(self._total_obs) + 1.0
        logt = math.log(t + 1.0)
        means = [0.0] * self._n_regions
        ucbs = [0.0] * self._n_regions
        c = self._ucb_c
        for i in range(self._n_regions):
            n = self._total_count[i]
            s = self._spot_count[i]
            mean = (s + 1.0) / (n + 2.0)
            bonus = c * math.sqrt(logt / (n + 1.0))
            ucb = mean + bonus
            if ucb > 1.0:
                ucb = 1.0
            means[i] = mean
            ucbs[i] = ucb
        return means, ucbs

    def _best_region_by_ucb(self, ucbs: list) -> int:
        best_i = 0
        best_v = ucbs[0]
        for i in range(1, self._n_regions):
            v = ucbs[i]
            if v > best_v:
                best_v = v
                best_i = i
        return best_i

    def _maybe_switch_region(self, target_idx: int, ucbs: list) -> None:
        cur = int(self.env.get_current_region())
        if target_idx == cur:
            return

        gap = float(self.env.gap_seconds)
        now = float(self.env.elapsed_seconds)
        if now - self._last_switch_elapsed < gap:
            return

        cur_ucb = ucbs[cur]
        tgt_ucb = ucbs[target_idx]

        if self._consec_no_spot >= 2:
            self.env.switch_region(int(target_idx))
            self._last_switch_elapsed = now
            self._consec_no_spot = 0
            return

        if tgt_ucb - cur_ucb >= 0.15:
            self.env.switch_region(int(target_idx))
            self._last_switch_elapsed = now
            self._consec_no_spot = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        cur_region = int(self.env.get_current_region())
        self._total_count[cur_region] += 1
        self._total_obs += 1
        if has_spot:
            self._spot_count[cur_region] += 1
            self._consec_no_spot = 0
        else:
            self._consec_no_spot += 1

        self._sync_work_done()

        elapsed = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        task_duration = float(self.task_duration)
        restart_overhead = float(self.restart_overhead)
        gap = float(self.env.gap_seconds)

        remaining_time = deadline - elapsed
        remaining_work = task_duration - self._work_done
        if remaining_work <= 1e-9:
            return self._CT_NONE
        if remaining_time <= 1e-9:
            return self._CT_NONE

        critical_window = 3.0 * gap + 6.0 * restart_overhead
        if (remaining_time <= remaining_work + critical_window) or self._locked_ondemand:
            self._locked_ondemand = True
            return self._CT_ON_DEMAND

        means, ucbs = self._region_scores()
        best_region = self._best_region_by_ucb(ucbs)
        p_best = ucbs[best_region]

        need_ondemand = (remaining_work > p_best * remaining_time)

        if has_spot:
            return self._CT_SPOT

        if need_ondemand:
            return self._CT_ON_DEMAND

        self._maybe_switch_region(best_region, ucbs)
        return self._CT_NONE