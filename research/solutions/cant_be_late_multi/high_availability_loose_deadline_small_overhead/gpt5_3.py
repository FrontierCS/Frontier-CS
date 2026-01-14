import json
from argparse import Namespace
import random

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_guard_heuristic_v1"

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

        # Lazy init fields (set on first _step call when env is available)
        self._region_inited = False
        self._prior_up = 2.0
        self._prior_down = 1.0
        self._rng = random.Random(0)

        self._last_done_len = 0
        self._done_sum = 0.0

        self.committed_od = False
        return self

    def _lazy_init_regions(self):
        if self._region_inited:
            return
        n = self.env.get_num_regions()
        self._region_obs = [0] * n
        self._region_up = [0] * n
        self._region_streak = [0] * n
        self._region_inited = True

    def _update_progress_cache(self):
        # Incremental sum of task_done_time
        L = len(self.task_done_time)
        if L > self._last_done_len:
            # Sum only new entries
            # Typically one entry per step; still robust if multiple
            delta = 0.0
            for i in range(self._last_done_len, L):
                delta += self.task_done_time[i]
            self._done_sum += delta
            self._last_done_len = L

    def _select_best_region(self, current_region: int) -> int:
        # Choose region with highest score = p_hat + 0.01 * streak
        # p_hat uses Beta prior smoothing
        n = len(self._region_obs)
        best_j = current_region
        best_score = -1.0
        for j in range(n):
            obs = self._region_obs[j]
            up = self._region_up[j]
            p_hat = (self._prior_up + up) / (self._prior_up + self._prior_down + obs)
            score = p_hat + 0.01 * self._region_streak[j]
            if score > best_score:
                best_score = score
                best_j = j
        return best_j

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy initialize region stats
        self._lazy_init_regions()

        # Update observed availability stats for current region
        cur_region = self.env.get_current_region()
        self._region_obs[cur_region] += 1
        if has_spot:
            self._region_up[cur_region] += 1
            self._region_streak[cur_region] += 1
        else:
            self._region_streak[cur_region] = 0

        # Update cached progress
        self._update_progress_cache()

        # Remaining work and time
        remaining_work = max(0.0, self.task_duration - self._done_sum)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_time <= 0:
            # Already at/past deadline; attempt to run ON_DEMAND
            self.committed_od = True
            return ClusterType.ON_DEMAND

        g = self.env.gap_seconds
        overhead_commit = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead

        # If already committed to OD, keep running OD to ensure finish
        if self.committed_od:
            return ClusterType.ON_DEMAND

        # Commit to OD if we cannot safely wait for another step
        # Safe to wait one more step iff remaining_time > remaining_work + overhead_commit + g
        if remaining_time <= remaining_work + overhead_commit + g + 1e-9:
            self.committed_od = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait if safe; try switching to a region with higher estimated availability
        target_region = self._select_best_region(cur_region)
        if target_region != cur_region:
            self.env.switch_region(target_region)

        return ClusterType.NONE