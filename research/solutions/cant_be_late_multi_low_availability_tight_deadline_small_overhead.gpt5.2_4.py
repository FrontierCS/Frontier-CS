import json
import math
from argparse import Namespace
from collections import deque
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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
        self._n_regions: int = 1
        self._succ: List[int] = []
        self._trial: List[int] = []
        self._total_obs: int = 0

        self._done_sum: float = 0.0
        self._last_done_len: int = 0

        self._commit_on_demand: bool = False

        self._unavail_streak_steps: int = 0
        self._last_switch_elapsed: float = -1e30
        self._switch_count: int = 0
        self._recent_regions: deque = deque(maxlen=4)

        self._cooldown_seconds: float = 600.0
        self._streak_threshold_seconds: float = 300.0
        self._switch_buffer_seconds: float = 1800.0

        self._bootstrap_until_elapsed: float = 600.0
        self._bootstrap_switch_interval: float = 30.0
        self._bootstrap_next_switch_time: float = 0.0

        return self

    def _lazy_init(self) -> None:
        if self._inited:
            return
        try:
            self._n_regions = int(self.env.get_num_regions())
        except Exception:
            self._n_regions = 1

        self._succ = [0] * self._n_regions
        self._trial = [0] * self._n_regions
        self._total_obs = 0

        o = float(self.restart_overhead)
        self._cooldown_seconds = max(600.0, 4.0 * o)
        self._streak_threshold_seconds = max(300.0, 2.0 * o)
        self._switch_buffer_seconds = max(1800.0, 10.0 * o)

        self._bootstrap_until_elapsed = min(600.0, 0.05 * float(self.deadline))
        self._bootstrap_switch_interval = max(30.0, 2.0 * float(self.env.gap_seconds))
        self._bootstrap_next_switch_time = 0.0

        self._inited = True

    def _update_done_sum(self) -> None:
        l = len(self.task_done_time)
        if l <= self._last_done_len:
            return
        # Usually one append per step; loop is O(total_steps) overall.
        for i in range(self._last_done_len, l):
            self._done_sum += float(self.task_done_time[i])
        self._last_done_len = l

    def _region_score(self, ridx: int) -> float:
        t = self._trial[ridx]
        s = self._succ[ridx]
        mean = (s + 1.0) / (t + 2.0)
        bonus = math.sqrt(math.log(self._total_obs + 2.0) / (t + 1.0))
        score = mean + 0.4 * bonus
        if ridx in self._recent_regions:
            # Small penalty to reduce ping-pong.
            score -= 0.05
        return score

    def _pick_best_region(self, current: int) -> int:
        if self._n_regions <= 1:
            return current
        best = current
        best_score = -1e30
        for i in range(self._n_regions):
            if i == current:
                continue
            sc = self._region_score(i)
            if sc > best_score:
                best_score = sc
                best = i
        return best

    def _maybe_switch_region_while_waiting(self, elapsed: float, time_left: float, remaining_work: float) -> None:
        if self._n_regions <= 1:
            return
        if self._switch_count >= 50:
            return
        if elapsed - self._last_switch_elapsed < self._cooldown_seconds:
            return
        if time_left <= remaining_work + float(self.restart_overhead) + self._switch_buffer_seconds:
            return
        if float(self.remaining_restart_overhead) > 0.0:
            return

        cur = int(self.env.get_current_region())

        # Bootstrap: quickly find any region with spot at the beginning.
        if self._done_sum <= 0.0 and elapsed <= self._bootstrap_until_elapsed:
            if elapsed >= self._bootstrap_next_switch_time:
                target = (cur + 1) % self._n_regions
                if target != cur:
                    self.env.switch_region(target)
                    self._recent_regions.append(cur)
                    self._last_switch_elapsed = elapsed
                    self._switch_count += 1
                    self._unavail_streak_steps = 0
                self._bootstrap_next_switch_time = elapsed + self._bootstrap_switch_interval
            return

        streak_seconds = self._unavail_streak_steps * float(self.env.gap_seconds)
        if streak_seconds < self._streak_threshold_seconds:
            return

        target = self._pick_best_region(cur)
        if target != cur:
            self.env.switch_region(target)
            self._recent_regions.append(cur)
            self._last_switch_elapsed = elapsed
            self._switch_count += 1
            self._unavail_streak_steps = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        cur = int(self.env.get_current_region())
        if 0 <= cur < self._n_regions:
            self._trial[cur] += 1
            if has_spot:
                self._succ[cur] += 1
            self._total_obs += 1

        if has_spot:
            self._unavail_streak_steps = 0
        else:
            self._unavail_streak_steps += 1

        self._update_done_sum()
        remaining_work = float(self.task_duration) - float(self._done_sum)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed
        gap = float(self.env.gap_seconds)
        o = float(self.restart_overhead)

        if time_left <= 0.0:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        safety = 2.0 * gap

        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        if time_left <= remaining_work + o + safety:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable.
        if time_left - gap > remaining_work + o + safety:
            self._maybe_switch_region_while_waiting(elapsed, time_left, remaining_work)
            return ClusterType.NONE

        self._commit_on_demand = True
        return ClusterType.ON_DEMAND