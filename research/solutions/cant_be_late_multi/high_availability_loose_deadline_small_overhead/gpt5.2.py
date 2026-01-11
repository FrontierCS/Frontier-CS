import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_multi_region_v2"

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

        self._done_work = 0.0
        self._last_done_len = 0

        self._gap_seconds = None
        self._safety_finish = None
        self._safety_lock = None
        self._switch_cooldown_seconds = None

        self._region_visits = None
        self._region_spot_yes = None
        self._no_spot_streak = 0
        self._last_switch_elapsed = -1e30

        self._on_demand_lock = False
        self._episode_started = False

        return self

    def _maybe_reset_episode_state(self):
        if self.env.elapsed_seconds <= 1e-9 and len(self.task_done_time) == 0:
            self._done_work = 0.0
            self._last_done_len = 0
            self._no_spot_streak = 0
            self._last_switch_elapsed = -1e30
            self._on_demand_lock = False

            n = self.env.get_num_regions()
            self._region_visits = [0] * n
            self._region_spot_yes = [0] * n

            self._episode_started = True

    def _update_done_work(self):
        td = self.task_done_time
        n = len(td)
        if n > self._last_done_len:
            s = 0.0
            for i in range(self._last_done_len, n):
                s += float(td[i])
            self._done_work += s
            self._last_done_len = n
        return self._done_work

    def _init_time_constants_if_needed(self):
        if self._gap_seconds is None:
            self._gap_seconds = float(self.env.gap_seconds)
            g = self._gap_seconds
            ro = float(self.restart_overhead)
            self._safety_finish = max(2.0 * ro, 0.25 * g)
            self._safety_lock = max(3.0 * ro, 1.0 * g)
            self._switch_cooldown_seconds = max(1.0 * g, 4.0 * ro)

    def _pick_region_to_switch(self, current_region: int):
        n_regions = self.env.get_num_regions()
        if n_regions <= 1:
            return None

        visits = self._region_visits
        yes = self._region_spot_yes
        total = 1
        for v in visits:
            total += v

        best_r = None
        best_score = -1e30
        log_total = math.log(total + 1.0)

        for r in range(n_regions):
            if r == current_region:
                continue
            n = visits[r]
            y = yes[r]
            mean = (y + 1.0) / (n + 2.0)
            bonus = math.sqrt(2.0 * log_total / (n + 1.0))
            score = mean + bonus
            if score > best_score:
                best_score = score
                best_r = r

        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_reset_episode_state()
        self._init_time_constants_if_needed()

        cur_region = self.env.get_current_region()
        if self._region_visits is None or len(self._region_visits) != self.env.get_num_regions():
            n = self.env.get_num_regions()
            self._region_visits = [0] * n
            self._region_spot_yes = [0] * n

        self._region_visits[cur_region] += 1
        if has_spot:
            self._region_spot_yes[cur_region] += 1
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1

        done_work = self._update_done_work()
        remaining_work = float(self.task_duration) - done_work
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        now = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - now
        if remaining_time <= 0.0:
            return ClusterType.NONE

        gap = self._gap_seconds
        ro = float(self.restart_overhead)

        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_if_od_now = max(0.0, float(self.remaining_restart_overhead))
        else:
            overhead_if_od_now = ro

        if not self._on_demand_lock:
            if remaining_time <= (remaining_work + overhead_if_od_now + self._safety_lock):
                self._on_demand_lock = True

        if self._on_demand_lock:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        can_wait_one = (remaining_time - gap) >= (remaining_work + ro + self._safety_finish)

        if can_wait_one:
            if (
                self.env.get_num_regions() > 1
                and self._no_spot_streak >= 1
                and (now - self._last_switch_elapsed) >= self._switch_cooldown_seconds
            ):
                target = self._pick_region_to_switch(cur_region)
                if target is not None and target != cur_region:
                    self.env.switch_region(target)
                    self._last_switch_elapsed = now
                    self._no_spot_streak = 0
            return ClusterType.NONE

        return ClusterType.ON_DEMAND