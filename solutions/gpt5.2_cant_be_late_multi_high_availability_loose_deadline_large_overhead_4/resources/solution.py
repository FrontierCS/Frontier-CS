import json
import math
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_safe_ucb_switch"

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

        self._mr_init = False
        self._done_work = 0.0
        self._task_done_len = 0
        self._step_count = 0
        self._committed_to_od = False
        self._region_spot_seen: List[int] = []
        self._region_total_seen: List[int] = []
        self._region_last_seen_step: List[int] = []
        return self

    def _lazy_init(self) -> None:
        if self._mr_init:
            return
        n = int(self.env.get_num_regions())
        self._region_spot_seen = [0] * n
        self._region_total_seen = [0] * n
        self._region_last_seen_step = [-10**9] * n
        self._mr_init = True

    def _update_done_work(self) -> None:
        td = self.task_done_time
        if td is None:
            return
        n = len(td)
        if n <= self._task_done_len:
            return
        s = 0.0
        for i in range(self._task_done_len, n):
            s += float(td[i])
        self._done_work += s
        self._task_done_len = n

    def _pick_next_region_ucb(self, cur_region: int) -> int:
        n = len(self._region_total_seen)
        if n <= 1:
            return cur_region

        t = self._step_count + 1
        logt = math.log(t + 1.0)

        best_r = cur_region
        best_score = -1e18

        c = 0.7
        for r in range(n):
            if r == cur_region:
                continue
            total = self._region_total_seen[r]
            spot = self._region_spot_seen[r]
            mean = (spot + 1.0) / (total + 2.0)
            bonus = c * math.sqrt(logt / (total + 1.0))
            score = mean + bonus

            if score > best_score:
                best_score = score
                best_r = r
            elif score == best_score:
                if self._region_last_seen_step[r] < self._region_last_seen_step[best_r]:
                    best_r = r
        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._step_count += 1

        cur_region = int(self.env.get_current_region())
        self._region_total_seen[cur_region] += 1
        if has_spot:
            self._region_spot_seen[cur_region] += 1
        self._region_last_seen_step[cur_region] = self._step_count

        self._update_done_work()

        remaining_work = float(self.task_duration) - float(self._done_work)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        if time_left <= 0.0:
            return ClusterType.NONE

        gap = float(self.env.gap_seconds)
        if not self._committed_to_od:
            # Ensure we don't miss the deadline due to step discretization or one restart.
            if time_left <= remaining_work + float(self.restart_overhead) + gap:
                self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self.env.get_num_regions() > 1:
            target = self._pick_next_region_ucb(cur_region)
            if target != cur_region:
                self.env.switch_region(int(target))

        return ClusterType.NONE
