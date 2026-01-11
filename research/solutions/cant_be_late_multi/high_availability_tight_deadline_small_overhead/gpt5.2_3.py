import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cb_late_multiregion_v3"

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

        self._done_total = 0.0
        self._done_len = 0
        self._last_progress_elapsed = 0.0

        self._regions_inited = False
        self._n_regions = 0
        self._spot_obs = None
        self._spot_succ = None

        self._ondemand_commit = False
        self._ondemand_until = -1.0

        self._searching = False
        self._search_start = 0.0
        self._last_switch_elapsed = -1e30

        self._spot_stable_count = 0.0

        self._gap = None
        self._buffer_s = None
        self._search_wait_cap = None
        self._od_burst = None
        self._revert_slack = None
        self._switch_cooldown = None

        return self

    def _lazy_init(self):
        if self._regions_inited:
            return
        n = int(self.env.get_num_regions())
        self._n_regions = n
        self._spot_obs = [0] * n
        self._spot_succ = [0] * n
        self._regions_inited = True

        self._gap = float(getattr(self.env, "gap_seconds", 1.0))
        ro = float(self.restart_overhead)

        self._buffer_s = max(300.0, 5.0 * ro, 2.0 * self._gap)
        self._search_wait_cap = max(600.0, 10.0 * ro, 30.0 * self._gap)
        self._od_burst = max(300.0, 3.0 * ro, 30.0 * self._gap)
        self._revert_slack = max(3600.0, 10.0 * ro, 120.0 * self._gap)
        self._switch_cooldown = max(1.0, ro)

    def _update_done_total(self):
        td = self.task_done_time
        ln = len(td)
        if ln <= self._done_len:
            return
        s = 0.0
        for i in range(self._done_len, ln):
            s += float(td[i])
        if s != 0.0:
            self._last_progress_elapsed = float(self.env.elapsed_seconds)
        self._done_total += s
        self._done_len = ln

    def _best_region_to_try(self, current_region: int) -> int:
        n = self._n_regions
        if n <= 1:
            return current_region

        total_obs = 0
        for v in self._spot_obs:
            total_obs += v
        total_obs = max(1, total_obs)

        log_total = math.log(total_obs + 1.0)
        c = 0.7

        best_r = current_region
        best_score = -1e100
        second_r = current_region
        second_score = -1e100

        for r in range(n):
            obs = self._spot_obs[r]
            succ = self._spot_succ[r]
            mean = (succ + 1.0) / (obs + 2.0)
            bonus = c * math.sqrt(log_total / (obs + 1.0))
            score = mean + bonus
            if score > best_score:
                second_score, second_r = best_score, best_r
                best_score, best_r = score, r
            elif score > second_score:
                second_score, second_r = score, r

        if best_r != current_region:
            return best_r
        if second_r != current_region:
            return second_r
        return (current_region + 1) % n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        elapsed = float(self.env.elapsed_seconds)
        current_region = int(self.env.get_current_region())

        self._spot_obs[current_region] += 1
        if has_spot:
            self._spot_succ[current_region] += 1
            self._spot_stable_count += 1.0
        else:
            self._spot_stable_count = 0.0

        self._update_done_total()

        remaining_work = float(self.task_duration) - self._done_total
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = float(self.deadline) - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        ro = float(self.restart_overhead)
        gap = self._gap
        buffer_s = self._buffer_s

        extra_if_start_od = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            extra_if_start_od = ro

        needed_if_od_now = remaining_work + extra_if_start_od
        slack = time_left - remaining_work

        urgent = time_left <= needed_if_od_now + buffer_s
        if urgent:
            self._ondemand_commit = True

        if self._ondemand_commit:
            self._searching = False
            return ClusterType.ON_DEMAND

        if elapsed < self._ondemand_until:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND and not self._ondemand_commit:
            if slack > self._revert_slack:
                stable_thresh = max(10.0 * gap, ro / 2.0)
                if has_spot and self._spot_stable_count >= stable_thresh:
                    self._searching = False
                    return ClusterType.SPOT
                if not has_spot:
                    self._searching = True
                    self._search_start = elapsed
                    if self._n_regions > 1 and (elapsed - self._last_switch_elapsed) >= self._switch_cooldown:
                        target = self._best_region_to_try(current_region)
                        if target != current_region:
                            self.env.switch_region(target)
                            self._last_switch_elapsed = elapsed
                    return ClusterType.NONE
            return ClusterType.ON_DEMAND

        if has_spot and slack > 0.0:
            self._searching = False
            return ClusterType.SPOT

        if slack <= 2.0 * buffer_s:
            self._searching = False
            self._ondemand_until = elapsed + self._od_burst
            return ClusterType.ON_DEMAND

        if not self._searching:
            self._searching = True
            self._search_start = elapsed

        max_wait = min(self._search_wait_cap, max(60.0, 0.25 * max(0.0, slack)))
        if (elapsed - self._search_start) >= max_wait:
            self._searching = False
            self._ondemand_until = elapsed + self._od_burst
            return ClusterType.ON_DEMAND

        if self._n_regions > 1 and (elapsed - self._last_switch_elapsed) >= self._switch_cooldown:
            target = self._best_region_to_try(current_region)
            if target != current_region:
                self.env.switch_region(target)
                self._last_switch_elapsed = elapsed

        return ClusterType.NONE