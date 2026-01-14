import json
import math
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_ucb_v1"

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
        self._committed_to_on_demand = False

        self._step_idx = 0

        self._done_cached = 0.0
        self._done_len_cached = 0

        self._region_total: List[int] = []
        self._region_spot: List[int] = []
        self._consec_no_spot: List[int] = []
        self._last_region: Optional[int] = None

        return self

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        n = int(self.env.get_num_regions())
        self._region_total = [0] * n
        self._region_spot = [0] * n
        self._consec_no_spot = [0] * n
        self._last_region = int(self.env.get_current_region())
        self._initialized = True

    def _scalar(self, x):
        if isinstance(x, (list, tuple)):
            return float(x[0])
        return float(x)

    def _update_done_cache(self) -> float:
        td = self.task_done_time
        ln = len(td)
        if ln > self._done_len_cached:
            s = 0.0
            for i in range(self._done_len_cached, ln):
                s += float(td[i])
            self._done_cached += s
            self._done_len_cached = ln
        return self._done_cached

    def _remaining_work_seconds(self) -> float:
        done = self._update_done_cache()
        td = self._scalar(self.task_duration)
        rem = td - done
        return rem if rem > 0.0 else 0.0

    def _should_commit_on_demand(self, last_cluster_type: ClusterType) -> bool:
        if self._committed_to_on_demand:
            return True

        rem_work = self._remaining_work_seconds()
        if rem_work <= 0.0:
            return False

        now = float(self.env.elapsed_seconds)
        deadline = self._scalar(self.deadline)
        rem_time = deadline - now

        gap = float(self.env.gap_seconds)
        overhead = self._scalar(self.restart_overhead)

        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_needed = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
            if overhead_needed < 0.0:
                overhead_needed = 0.0
        else:
            overhead_needed = overhead

        buffer = 3.0 * gap
        min_needed = rem_work + overhead_needed + buffer

        return rem_time <= min_needed

    def _pick_next_region_ucb(self, cur_region: int) -> int:
        n = len(self._region_total)
        if n <= 1:
            return cur_region

        total_obs = sum(self._region_total) + 1

        best_r = cur_region
        best_score = -1e30

        c = 0.85
        for r in range(n):
            if r == cur_region:
                continue
            tr = self._region_total[r]
            sr = self._region_spot[r]
            mean = (sr + 1.0) / (tr + 2.0)
            bonus = c * math.sqrt(math.log(total_obs + 1.0) / (tr + 1.0))
            score = mean + bonus
            if score > best_score:
                best_score = score
                best_r = r

        if best_r == cur_region:
            best_r = (cur_region + 1) % n
        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._step_idx += 1

        cur_region = int(self.env.get_current_region())
        self._last_region = cur_region

        self._region_total[cur_region] += 1
        if has_spot:
            self._region_spot[cur_region] += 1
            self._consec_no_spot[cur_region] = 0
        else:
            self._consec_no_spot[cur_region] += 1

        rem_work = self._remaining_work_seconds()
        if rem_work <= 0.0:
            return ClusterType.NONE

        if self._should_commit_on_demand(last_cluster_type):
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        next_region = self._pick_next_region_ucb(cur_region)
        if next_region != cur_region:
            self.env.switch_region(next_region)
        return ClusterType.NONE