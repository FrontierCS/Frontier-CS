import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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
        self._num_regions = 1
        self._done_sum = 0.0
        self._last_done_len = 0

        self._ema_alpha = 0.08
        self._region_ema = None
        self._region_visits = None
        self._no_spot_streak = None

        self._last_switch_elapsed = -1e30
        self._panic_mode = False
        return self

    def _maybe_init(self):
        if self._inited:
            return
        env = self.env
        try:
            self._num_regions = int(env.get_num_regions())
        except Exception:
            self._num_regions = 1
        if self._num_regions <= 0:
            self._num_regions = 1
        self._region_ema = [0.55] * self._num_regions
        self._region_visits = [0] * self._num_regions
        self._no_spot_streak = [0] * self._num_regions
        self._inited = True

    def _update_done_sum(self):
        td = self.task_done_time
        n = len(td)
        if n <= self._last_done_len:
            return
        s = 0.0
        for i in range(self._last_done_len, n):
            s += td[i]
        self._done_sum += s
        self._last_done_len = n

    def _select_best_region(self, cur_region: int) -> int:
        best_idx = cur_region
        best_score = -1e18
        ema = self._region_ema
        visits = self._region_visits
        for i in range(self._num_regions):
            v = visits[i]
            bonus = 0.10 / math.sqrt(v + 1.0)
            score = ema[i] + bonus
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_init()
        self._update_done_sum()

        env = self.env
        gap = float(env.gap_seconds)
        elapsed = float(env.elapsed_seconds)
        deadline = float(self.deadline)
        task_duration = float(self.task_duration)
        ro = float(self.restart_overhead)

        remaining_work = task_duration - self._done_sum
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            return ClusterType.NONE

        try:
            cur_region = int(env.get_current_region())
        except Exception:
            cur_region = 0
        if cur_region < 0 or cur_region >= self._num_regions:
            cur_region = 0

        # Update region availability estimates (only for current observed region).
        visits = self._region_visits
        ema = self._region_ema
        visits[cur_region] += 1
        obs = 1.0 if has_spot else 0.0
        a = self._ema_alpha
        ema[cur_region] = (1.0 - a) * ema[cur_region] + a * obs

        streaks = self._no_spot_streak
        if has_spot:
            streaks[cur_region] = 0
        else:
            streaks[cur_region] += 1

        if self._panic_mode:
            return ClusterType.ON_DEMAND

        # Conservative deadline protection.
        # Start on-demand when slack becomes small to avoid penalty.
        # slack = remaining_time - remaining_work
        margin = 4.0 * gap + 3.0 * ro
        if remaining_time <= remaining_work + margin:
            self._panic_mode = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # Spot not available: wait, but consider switching regions to find spot sooner.
        if self._num_regions > 1:
            # Switch after some consecutive no-spot observations, not too frequently.
            switch_after = max(2, int(math.ceil((2.0 * ro) / max(gap, 1e-9))) + 1)
            min_interval = 6.0 * gap
            if streaks[cur_region] >= switch_after and (elapsed - self._last_switch_elapsed) >= min_interval:
                target = self._select_best_region(cur_region)
                if target != cur_region:
                    try:
                        env.switch_region(target)
                        self._last_switch_elapsed = elapsed
                    except Exception:
                        pass

        return ClusterType.NONE
