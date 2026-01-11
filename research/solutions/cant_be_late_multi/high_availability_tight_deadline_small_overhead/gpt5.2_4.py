import json
from argparse import Namespace
from typing import Optional, List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multiregion_v1"

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
        self._inited = True
        self._num_regions = int(self.env.get_num_regions())
        self._done_len = 0
        self._work_done = 0.0
        self._none_waste_seconds = 0.0
        self._last_elapsed: Optional[float] = None
        self._critical_mode = False

        task_duration = self._get_task_duration()
        deadline = float(self.deadline)
        total_slack = max(0.0, deadline - task_duration)

        self._critical_slack = max(3600.0, 0.15 * total_slack)
        self._max_wait_budget = max(0.0, total_slack - self._critical_slack)

        self._obs_total = [0] * self._num_regions
        self._obs_true = [0] * self._num_regions

    def _get_task_duration(self) -> float:
        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            return float(td[0]) if td else 0.0
        return float(td)

    def _update_work_done(self) -> None:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            self._done_len = 0
            self._work_done = 0.0
            return
        n = len(tdt)
        if n > self._done_len:
            self._work_done += float(sum(tdt[self._done_len:n]))
            self._done_len = n

    def _region_score(self, idx: int) -> float:
        # Beta(1,1) prior mean
        tot = self._obs_total[idx]
        tru = self._obs_true[idx]
        return (tru + 1.0) / (tot + 2.0)

    def _pick_next_region(self, current: int) -> int:
        if self._num_regions <= 1:
            return current
        best_idx = -1
        best_score = -1.0
        for i in range(self._num_regions):
            if i == current:
                continue
            s = self._region_score(i)
            if s > best_score:
                best_score = s
                best_idx = i
        if best_idx < 0:
            return (current + 1) % self._num_regions
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, "_inited") or not self._inited:
            self._lazy_init()

        now = float(self.env.elapsed_seconds)
        if self._last_elapsed is not None:
            dt = now - self._last_elapsed
            if dt > 0 and last_cluster_type == ClusterType.NONE:
                self._none_waste_seconds += dt
        self._last_elapsed = now

        region = int(self.env.get_current_region())
        if 0 <= region < self._num_regions:
            self._obs_total[region] += 1
            if has_spot:
                self._obs_true[region] += 1

        self._update_work_done()
        task_duration = self._get_task_duration()
        remaining_work = task_duration - self._work_done
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        remaining_time = float(self.deadline) - now
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        if pending_overhead < 0:
            pending_overhead = 0.0

        safe_slack = remaining_time - (remaining_work + pending_overhead)

        if (not self._critical_mode) and (safe_slack <= self._critical_slack):
            self._critical_mode = True

        if self._critical_mode:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        allow_wait = (
            safe_slack > (self._critical_slack + max(gap, 1e-9))
            and self._none_waste_seconds < self._max_wait_budget
        )

        if allow_wait:
            next_region = self._pick_next_region(region)
            if next_region != region:
                self.env.switch_region(next_region)
            return ClusterType.NONE

        self._critical_mode = True
        return ClusterType.ON_DEMAND