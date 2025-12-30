import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region"

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

    def _get_scalar(self, x):
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _lazy_init(self):
        if getattr(self, "_inited", False):
            return
        self._inited = True

        n = int(self.env.get_num_regions())
        self._num_regions = n
        self._avail: List[int] = [0] * n
        self._seen: List[int] = [0] * n
        self._last_visit: List[float] = [-1.0] * n

        self._last_task_done_len = 0
        self._work_done = 0.0

        self._forced_on_demand = False

        self._consec_no_spot = 0.0
        self._last_switch_time = -1e30

        self._deadline_s = self._get_scalar(self.deadline)
        self._task_duration_s = self._get_scalar(self.task_duration)
        self._restart_overhead_s = self._get_scalar(self.restart_overhead)

        gap = float(self.env.gap_seconds)
        self._switch_cooldown_s = max(5.0 * gap, min(30.0, 30.0 * gap))
        self._switch_after_no_spot_s = max(3.0 * gap, 15.0)

        self._safety_slack_s = max(1800.0, 20.0 * self._restart_overhead_s)

    def _update_work_done(self):
        td = self.task_done_time
        l = len(td)
        if l <= self._last_task_done_len:
            return
        s = 0.0
        for i in range(self._last_task_done_len, l):
            s += float(td[i])
        self._work_done += s
        self._last_task_done_len = l

    def _region_score(self, idx: int, now: float) -> float:
        seen = self._seen[idx]
        avail = self._avail[idx]
        p = (avail + 1.0) / (seen + 2.0)
        explore = 0.25 if seen == 0 else 0.0
        lv = self._last_visit[idx]
        if lv < 0.0:
            rec = 1.0
        else:
            rec = min(1.0, (now - lv) / 3600.0)
        return p + explore + 0.05 * rec

    def _choose_best_region(self, now: float, exclude: Optional[int] = None) -> int:
        best_idx = 0
        best_score = -1e100
        for i in range(self._num_regions):
            if exclude is not None and i == exclude:
                continue
            sc = self._region_score(i, now)
            if sc > best_score:
                best_score = sc
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        now = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)

        self._update_work_done()

        remaining_work = self._task_duration_s - self._work_done
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self._deadline_s - now
        if time_left <= 0.0:
            return ClusterType.NONE

        cur_region = int(self.env.get_current_region())
        self._seen[cur_region] += 1
        if has_spot:
            self._avail[cur_region] += 1
            self._consec_no_spot = 0.0
        else:
            self._consec_no_spot += gap
        self._last_visit[cur_region] = now

        # If we are so close that switching to on-demand (incurring a restart overhead)
        # could make it impossible to finish, prefer continuing current cluster if it can run.
        keep_overhead = 0.0
        if last_cluster_type == ClusterType.NONE:
            keep_overhead = self._restart_overhead_s
        else:
            keep_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

        t_needed_keep = remaining_work + keep_overhead
        t_needed_od = remaining_work + (keep_overhead if last_cluster_type == ClusterType.ON_DEMAND else self._restart_overhead_s)

        # Critical: no time to restart; keep current if possible.
        if time_left <= t_needed_od and time_left >= t_needed_keep:
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND

        # Decide when to force on-demand to guarantee completion.
        if not self._forced_on_demand:
            if time_left <= (t_needed_od + self._safety_slack_s):
                self._forced_on_demand = True

        if self._forced_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # No spot and not forced on-demand: pause to save cost, and opportunistically switch regions.
        # Avoid switching if we're mid-overhead (switching would reset overhead back to full).
        rem_ov = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        avoid_switch = (rem_ov > 0.0) and (rem_ov < max(0.0, self._restart_overhead_s - gap))

        if (self._num_regions > 1) and (not avoid_switch):
            if (now - self._last_switch_time) >= self._switch_cooldown_s and self._consec_no_spot >= self._switch_after_no_spot_s:
                target = self._choose_best_region(now, exclude=cur_region)
                if target != cur_region:
                    self.env.switch_region(target)
                    self._last_switch_time = now
                    self._consec_no_spot = 0.0

        return ClusterType.NONE