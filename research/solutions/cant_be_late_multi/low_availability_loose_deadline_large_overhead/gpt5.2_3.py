import json
import math
from argparse import Namespace
from typing import Optional

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
        return self

    def _lazy_init(self) -> None:
        if getattr(self, "_inited", False):
            return
        self._inited = True

        try:
            self._nregions = int(self.env.get_num_regions())
        except Exception:
            self._nregions = 1

        self._t = 0
        self._region_n = [0] * self._nregions
        self._region_s = [0] * self._nregions
        self._last_region = None

        self._committed_on_demand = False
        self._consecutive_no_spot = 0
        self._last_switch_elapsed = -1e30

        self._work_done = 0.0
        self._last_done_len = 0

    @staticmethod
    def _as_float_scalar(x) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _update_work_done(self) -> None:
        td = self.task_done_time
        ln = len(td)
        if ln > self._last_done_len:
            self._work_done += sum(td[self._last_done_len : ln])
            self._last_done_len = ln

    def _ucb_region(self, current_region: int) -> int:
        if self._nregions <= 1:
            return current_region
        t = max(1, self._t)
        best_r = current_region
        best_score = -1e100
        c = 0.85
        alpha = 1.0
        for r in range(self._nregions):
            n = self._region_n[r]
            s = self._region_s[r]
            mean = (s + alpha) / (n + 2.0 * alpha)
            bonus = c * math.sqrt(math.log(t + 1.0) / (n + 1.0))
            score = mean + bonus
            if r == current_region:
                score += 0.02
            if score > best_score:
                best_score = score
                best_r = r
        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_work_done()

        self._t += 1

        cur_region = int(self.env.get_current_region())
        if 0 <= cur_region < self._nregions:
            self._region_n[cur_region] += 1
            if has_spot:
                self._region_s[cur_region] += 1

        if has_spot:
            self._consecutive_no_spot = 0
        else:
            self._consecutive_no_spot += 1

        task_duration = self._as_float_scalar(self.task_duration)
        deadline = self._as_float_scalar(self.deadline)
        restart_overhead = self._as_float_scalar(self.restart_overhead)
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))

        remaining_work = task_duration - self._work_done
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        pending = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        pending = max(0.0, min(pending, restart_overhead))

        if last_cluster_type == ClusterType.ON_DEMAND:
            required_on_demand = remaining_work + pending
        else:
            required_on_demand = remaining_work + restart_overhead

        safety_margin = max(2.0 * gap, 2.0 * restart_overhead, 1800.0)

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        if time_left <= required_on_demand + safety_margin:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Not urgent; try to avoid paying for overhead time if any is pending.
        if pending > 0.0:
            return ClusterType.NONE

        if has_spot:
            return ClusterType.SPOT

        slack_vs_commit = time_left - required_on_demand

        # If we have plenty of slack, explore other regions for spot by switching and idling this step.
        probe_threshold = safety_margin + gap + restart_overhead
        if self._nregions > 1 and slack_vs_commit > probe_threshold:
            patience = 2
            if self._consecutive_no_spot >= patience:
                target = self._ucb_region(cur_region)
                if target == cur_region:
                    target = (cur_region + 1) % self._nregions
                if target != cur_region:
                    self.env.switch_region(int(target))
                    self._consecutive_no_spot = 0
                    self._last_switch_elapsed = elapsed
                    return ClusterType.NONE

        return ClusterType.NONE