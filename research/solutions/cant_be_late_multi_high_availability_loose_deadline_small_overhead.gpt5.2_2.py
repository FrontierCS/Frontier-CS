import json
import math
from argparse import Namespace
from typing import List, Optional

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
        self._reset_internal_state()
        return self

    def _reset_internal_state(self) -> None:
        self._inited: bool = False
        self._num_regions: int = 0
        self._alpha: List[float] = []
        self._beta: List[float] = []
        self._step_count: int = 0
        self._no_spot_streak: int = 0
        self._switch_cooldown: int = 0

        self._last_done_len: int = 0
        self._work_done: float = 0.0

        self._committed_on_demand: bool = False

        self._CT_NONE: Optional[ClusterType] = None
        self._CT_SPOT: ClusterType = ClusterType.SPOT
        self._CT_OD: ClusterType = ClusterType.ON_DEMAND

    def _lazy_init(self) -> None:
        if self._inited:
            return
        self._CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None"))
        self._num_regions = int(self.env.get_num_regions())
        self._alpha = [1.0] * self._num_regions
        self._beta = [1.0] * self._num_regions
        self._step_count = 0
        self._no_spot_streak = 0
        self._switch_cooldown = 0
        self._last_done_len = 0
        self._work_done = 0.0
        self._committed_on_demand = False
        self._inited = True

    def _update_work_done(self) -> None:
        lst = self.task_done_time
        n = len(lst)
        if n == self._last_done_len:
            return
        if n < self._last_done_len:
            self._work_done = float(sum(lst))
            self._last_done_len = n
            return
        self._work_done += float(sum(lst[self._last_done_len : n]))
        self._last_done_len = n

    def _spot_mean(self, i: int) -> float:
        a = self._alpha[i]
        b = self._beta[i]
        return a / (a + b)

    def _select_region_ucb(self, exclude: int) -> int:
        t = self._step_count + 1
        logt = math.log(t + 1.0)
        best_i = exclude
        best_score = -1e18
        c = 0.35
        for i in range(self._num_regions):
            if i == exclude:
                continue
            a = self._alpha[i]
            b = self._beta[i]
            n = max(1.0, (a + b - 2.0))
            mean = a / (a + b)
            score = mean + c * math.sqrt(logt / n)
            if score > best_score:
                best_score = score
                best_i = i
        return best_i

    def _required_time_if_commit_od(self, last_cluster_type: ClusterType, remaining_work: float, gap: float) -> float:
        if last_cluster_type == self._CT_OD:
            overhead = float(self.remaining_restart_overhead or 0.0)
        else:
            overhead = float(self.restart_overhead or 0.0)
        total = max(0.0, overhead) + max(0.0, remaining_work)
        if total <= 0.0:
            return 0.0
        steps = int(math.ceil(total / gap))
        return float(steps) * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._step_count += 1

        gap = float(self.env.gap_seconds)
        if gap <= 0.0:
            gap = 1.0

        self._update_work_done()
        remaining_work = float(self.task_duration) - float(self._work_done)
        if remaining_work <= 0.0:
            return self._CT_NONE  # type: ignore[return-value]

        now = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - now
        if time_left <= 0.0:
            return self._CT_NONE  # type: ignore[return-value]

        cur_region = int(self.env.get_current_region())
        if 0 <= cur_region < self._num_regions:
            if has_spot:
                self._alpha[cur_region] += 1.0
                self._no_spot_streak = 0
            else:
                self._beta[cur_region] += 1.0
                self._no_spot_streak += 1

        if self._switch_cooldown > 0:
            self._switch_cooldown -= 1

        if self._committed_on_demand:
            return self._CT_OD

        if not has_spot:
            required_od_time = self._required_time_if_commit_od(last_cluster_type, remaining_work, gap)
            buffer_steps = 2.0
            if required_od_time + buffer_steps * gap >= time_left:
                self._committed_on_demand = True
                return self._CT_OD

            if self._num_regions > 1 and self._switch_cooldown == 0:
                if self._no_spot_streak >= 3:
                    best = self._select_region_ucb(exclude=cur_region)
                    if best != cur_region:
                        self.env.switch_region(best)
                        self._switch_cooldown = max(2, int(round(float(self.restart_overhead) / gap)) + 1)
                        self._no_spot_streak = 0

            return self._CT_NONE  # type: ignore[return-value]

        if last_cluster_type == self._CT_OD:
            slack = time_left - remaining_work
            if slack <= 0.0:
                self._committed_on_demand = True
                return self._CT_OD
            if slack <= (float(self.restart_overhead) + 2.0 * gap):
                return self._CT_OD
            return self._CT_SPOT

        return self._CT_SPOT
