import json
import math
from argparse import Namespace
from typing import Optional, List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = getattr(ClusterType, "SPOT")
_CT_OD = getattr(ClusterType, "ON_DEMAND")
_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None"))


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
        return self

    def _ensure_init(self) -> None:
        if getattr(self, "_inited", False):
            return
        self._inited = True

        self._n_regions = int(self.env.get_num_regions())
        if self._n_regions <= 0:
            self._n_regions = 1

        self._alpha = 0.06
        self._ucb_c = 0.28
        self._ema: List[float] = [0.5] * self._n_regions
        self._count: List[int] = [0] * self._n_regions

        self._mode_od_commit = False

        self._task_done_sum = 0.0
        self._task_done_len = 0

        self._no_spot_streak = 0
        self._last_region_switch_elapsed = -1e30
        self._rr_idx = 0

        gap = float(getattr(self.env, "gap_seconds", 3600.0))
        self._gap = gap

        self._cooldown_seconds = max(1800.0, 2.0 * float(self.restart_overhead))
        self._switch_no_spot_seconds = max(3600.0, 4.0 * float(self.restart_overhead))

    def _update_task_done(self) -> float:
        td = self.task_done_time
        n = len(td)
        if n == self._task_done_len:
            return self._task_done_sum
        if n < self._task_done_len:
            s = 0.0
            for x in td:
                s += float(x)
            self._task_done_sum = s
            self._task_done_len = n
            return s
        s = self._task_done_sum
        for i in range(self._task_done_len, n):
            s += float(td[i])
        self._task_done_sum = s
        self._task_done_len = n
        return s

    def _pick_region(self, current: int) -> int:
        total = 1
        for c in self._count:
            total += c
        logt = math.log(total + 1.0)

        best_idx = current
        best_score = -1e30

        # If there are unvisited regions, try them first with light round-robin bias.
        any_unvisited = False
        for c in self._count:
            if c == 0:
                any_unvisited = True
                break
        if any_unvisited:
            start = self._rr_idx % self._n_regions
            for k in range(self._n_regions):
                i = (start + k) % self._n_regions
                if self._count[i] == 0:
                    self._rr_idx = i + 1
                    return i

        for i in range(self._n_regions):
            c = self._count[i]
            bonus = self._ucb_c * math.sqrt(logt / (c + 1.0))
            score = self._ema[i] + bonus
            if i == current:
                score += 0.015
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _maybe_switch_region_while_waiting(self, current_region: int) -> None:
        if self._n_regions <= 1:
            return
        if float(self.remaining_restart_overhead) > 0.0:
            return
        now = float(self.env.elapsed_seconds)
        if now - self._last_region_switch_elapsed < self._cooldown_seconds:
            return
        if self._no_spot_streak * self._gap < self._switch_no_spot_seconds:
            return

        target = self._pick_region(current_region)
        if target != current_region:
            self.env.switch_region(int(target))
            self._last_region_switch_elapsed = now
            self._no_spot_streak = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        # Update region stats with the observation for the *current* region.
        cur_region = int(self.env.get_current_region())
        if 0 <= cur_region < self._n_regions:
            self._count[cur_region] += 1
            x = 1.0 if has_spot else 0.0
            a = self._alpha
            self._ema[cur_region] = (1.0 - a) * self._ema[cur_region] + a * x

        # Cache work done efficiently.
        work_done = self._update_task_done()

        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed
        if remaining_time < 0.0:
            remaining_time = 0.0

        remaining_work = float(self.task_duration) - float(work_done)
        if remaining_work < 0.0:
            remaining_work = 0.0

        if remaining_work <= 0.0:
            return _CT_NONE

        pending_oh = float(self.remaining_restart_overhead)
        gap = self._gap
        restart_oh = float(self.restart_overhead)

        # Safety buffers for discretization + restart overhead.
        buffer_time = max(2.0 * gap, 1.5 * restart_oh)

        # If already committed to on-demand, stick to it.
        if self._mode_od_commit:
            if pending_oh > 0.0:
                return _CT_OD
            return _CT_OD

        # During an active restart overhead, avoid actions that can reset it unless forced.
        if pending_oh > 0.0:
            if last_cluster_type == _CT_OD:
                return _CT_OD
            if last_cluster_type == _CT_SPOT and has_spot:
                return _CT_SPOT
            # Can't continue spot; safest is on-demand.
            return _CT_OD

        # Decide whether we must switch to on-demand to guarantee finishing.
        need_overhead_if_od = 0.0 if last_cluster_type == _CT_OD else restart_oh
        if remaining_time <= remaining_work + need_overhead_if_od + buffer_time:
            self._mode_od_commit = True
            return _CT_OD

        # Not urgent: prefer spot when available, otherwise wait (pause) to save cost.
        if has_spot:
            self._no_spot_streak = 0
            return _CT_SPOT

        self._no_spot_streak += 1
        self._maybe_switch_region_while_waiting(cur_region)
        return _CT_NONE
