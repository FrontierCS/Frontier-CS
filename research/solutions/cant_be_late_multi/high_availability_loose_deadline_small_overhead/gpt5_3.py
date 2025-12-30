import json
import math
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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

        # Internal state
        self._num_regions: Optional[int] = None
        self._region_counts = None
        self._region_spot_counts = None
        self._ewma = None
        self._preferred_region: Optional[int] = None

        self._prev_segments_len = 0
        self._accum_done_seconds = 0.0
        self._lock_od = False

        return self

    def _init_regions_if_needed(self):
        if self._num_regions is None:
            try:
                self._num_regions = self.env.get_num_regions()
            except Exception:
                self._num_regions = 1
            self._region_counts = [0] * self._num_regions
            self._region_spot_counts = [0] * self._num_regions
            # Start optimistic due to high spot availability in traces
            self._ewma = [0.6] * self._num_regions
            self._preferred_region = self.env.get_current_region()

    def _update_progress_sum(self):
        # Incrementally track total productive work to avoid O(n) sum per step
        cur_len = len(self.task_done_time)
        if cur_len > self._prev_segments_len:
            added = 0.0
            for i in range(self._prev_segments_len, cur_len):
                added += float(self.task_done_time[i])
            self._accum_done_seconds += added
            self._prev_segments_len = cur_len

    def _select_best_region(self, current_region: int) -> int:
        # Choose region with highest EWMA; tie-breaker by larger sample count, then lower index
        best = current_region
        best_score = self._ewma[best]
        best_count = self._region_counts[best]
        for i in range(self._num_regions):
            score = self._ewma[i]
            count = self._region_counts[i]
            if score > best_score + 1e-12:
                best = i
                best_score = score
                best_count = count
            elif abs(score - best_score) < 1e-12:
                if count > best_count or (count == best_count and i < best):
                    best = i
                    best_score = score
                    best_count = count
        return best

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_regions_if_needed()
        self._update_progress_sum()

        cur_region = self.env.get_current_region()

        # Update observed availability stats for current region (EWMA)
        self._region_counts[cur_region] += 1
        if has_spot:
            self._region_spot_counts[cur_region] += 1
            self._ewma[cur_region] = self._ewma[cur_region] * 0.95 + 0.05 * 1.0
        else:
            self._ewma[cur_region] = self._ewma[cur_region] * 0.95 + 0.05 * 0.0

        # Compute remaining work and time
        gap = float(self.env.gap_seconds)
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        rem_work = max(0.0, float(self.task_duration) - self._accum_done_seconds)

        if rem_work <= 1e-9:
            return ClusterType.NONE

        # Time needed to finish on on-demand if we switch/continue now (with pending overhead considered)
        if last_cluster_type == ClusterType.ON_DEMAND:
            od_overhead = float(self.remaining_restart_overhead)
        else:
            od_overhead = float(self.restart_overhead)

        od_steps_needed = 0 if rem_work + od_overhead <= 0 else math.ceil((rem_work + od_overhead) / gap)
        od_time_needed = od_steps_needed * gap

        # If we are in critical zone, commit to on-demand
        if self._lock_od or time_left <= od_time_needed + 1e-9:
            self._lock_od = True
            return ClusterType.ON_DEMAND

        # Prefer spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide to wait (NONE) or use on-demand
        # We can afford to wait one step if after waiting we still have enough time to finish on OD
        if time_left - gap >= od_time_needed + 1e-9:
            # Pre-position to best region for next step
            best_region = self._select_best_region(cur_region)
            if best_region != cur_region:
                self.env.switch_region(best_region)
            return ClusterType.NONE
        else:
            # Not enough slack to wait: go ON_DEMAND and lock to finish
            self._lock_od = True
            return ClusterType.ON_DEMAND