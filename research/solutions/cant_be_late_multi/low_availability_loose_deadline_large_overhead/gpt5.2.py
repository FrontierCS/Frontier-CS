import json
import math
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = getattr(ClusterType, "SPOT")
_CT_ON_DEMAND = getattr(ClusterType, "ON_DEMAND")
_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None"))


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

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

        self._inited: bool = False
        self._num_regions: int = 0

        self._td_len: int = 0
        self._work_done: float = 0.0

        self._n: List[int] = []
        self._s: List[int] = []
        self._ewma: List[float] = []
        self._total_obs: int = 0

        self._prior_p: float = 0.25
        self._ewma_lr: float = 0.02
        self._ucb_c: float = 0.18

        self._no_spot_streak: int = 0
        self._switch_after_streak: int = 2

        self._od_hold_steps: int = 0
        self._spot_ready_steps: int = 0
        self._k_hold: int = 1
        self._k_ready: int = 1

        return self

    def _lazy_init(self) -> None:
        if self._inited:
            return
        self._num_regions = int(self.env.get_num_regions())
        if self._num_regions <= 0:
            self._num_regions = 1
        self._n = [0] * self._num_regions
        self._s = [0] * self._num_regions
        self._ewma = [float(self._prior_p)] * self._num_regions
        self._total_obs = 0
        self._no_spot_streak = 0

        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        overhead = float(self.restart_overhead)

        base = int(math.ceil(overhead / gap)) if gap > 0 else 1
        if base < 1:
            base = 1
        self._k_hold = base
        self._k_ready = base

        self._switch_after_streak = 2 if base <= 1 else min(8, base + 1)

        self._inited = True

    def _update_work_done(self) -> None:
        td = self.task_done_time
        if td is None:
            return
        l = len(td)
        if l > self._td_len:
            self._work_done += sum(td[self._td_len : l])
            self._td_len = l

    def _pick_next_region(self, current: int) -> int:
        if self._num_regions <= 1:
            return current
        total = self._total_obs + 1
        logt = math.log(total + 1.0)

        best_idx = current
        best_score = -1e30
        for i in range(self._num_regions):
            if i == current:
                continue
            ni = self._n[i]
            score = self._ewma[i] + self._ucb_c * math.sqrt(logt / (ni + 1.0))
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        cur_region = int(self.env.get_current_region())
        if cur_region < 0 or cur_region >= self._num_regions:
            cur_region = 0

        self._update_work_done()

        remaining_work = float(self.task_duration) - float(self._work_done)
        if remaining_work <= 1e-9:
            return _CT_NONE

        now = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        time_left = deadline - now

        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        overhead = float(self.restart_overhead)

        self._total_obs += 1
        self._n[cur_region] += 1
        if has_spot:
            self._s[cur_region] += 1

        prev = self._ewma[cur_region]
        x = 1.0 if has_spot else 0.0
        self._ewma[cur_region] = prev + self._ewma_lr * (x - prev)

        if has_spot:
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1

        critical_needed = remaining_work + overhead + 2.0 * gap

        if time_left <= critical_needed:
            self._od_hold_steps = max(self._od_hold_steps, self._k_hold)
            self._spot_ready_steps = 0
            return _CT_ON_DEMAND

        if self.remaining_restart_overhead > 0 and last_cluster_type in (_CT_ON_DEMAND, _CT_SPOT):
            if last_cluster_type == _CT_ON_DEMAND:
                if has_spot:
                    self._spot_ready_steps += 1
                else:
                    self._spot_ready_steps = 0
                return _CT_ON_DEMAND
            if last_cluster_type == _CT_SPOT and has_spot:
                return _CT_SPOT

        if self._od_hold_steps > 0:
            self._od_hold_steps -= 1
            if has_spot:
                self._spot_ready_steps += 1
            else:
                self._spot_ready_steps = 0
            return _CT_ON_DEMAND

        if last_cluster_type == _CT_ON_DEMAND:
            if has_spot:
                self._spot_ready_steps += 1
            else:
                self._spot_ready_steps = 0

            switch_back_needed = remaining_work + 2.0 * overhead + 3.0 * gap
            if has_spot and self._spot_ready_steps >= self._k_ready and time_left > switch_back_needed:
                self._spot_ready_steps = 0
                return _CT_SPOT
            return _CT_ON_DEMAND

        if has_spot:
            return _CT_SPOT

        if time_left - gap > critical_needed:
            if self._num_regions > 1 and self.remaining_restart_overhead <= 0:
                if self._no_spot_streak >= self._switch_after_streak:
                    nxt = self._pick_next_region(cur_region)
                    if nxt != cur_region:
                        self.env.switch_region(nxt)
                    self._no_spot_streak = 0
            return _CT_NONE

        self._od_hold_steps = self._k_hold
        self._spot_ready_steps = 0
        return _CT_ON_DEMAND