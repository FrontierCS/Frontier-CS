import json
from argparse import Namespace
from typing import Optional, List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_ai_01"

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
        self._committed_on_demand: bool = False
        self._prev_progress_len: int = 0
        self._accum_progress: float = 0.0
        self._region_stats_initialized: bool = False
        self._region_avail: Optional[List[int]] = None
        self._region_total: Optional[List[int]] = None

        return self

    def _init_region_stats_if_needed(self):
        if not self._region_stats_initialized:
            try:
                n = self.env.get_num_regions()
            except Exception:
                n = 1
            self._region_avail = [0] * n
            self._region_total = [0] * n
            self._region_stats_initialized = True

    def _update_progress_accumulator(self):
        # Incrementally update accumulated progress to avoid repeated full sums
        current_len = len(self.task_done_time)
        if current_len > self._prev_progress_len:
            newly_done = self.task_done_time[self._prev_progress_len:current_len]
            if newly_done:
                self._accum_progress += sum(newly_done)
            self._prev_progress_len = current_len

    def _select_best_region(self, current_idx: int) -> int:
        # Choose the region with the highest observed spot availability ratio
        # Fallback to next region on ties or if stats are zero.
        try:
            n = self.env.get_num_regions()
        except Exception:
            return current_idx
        if n <= 1 or self._region_avail is None or self._region_total is None:
            return current_idx

        best_idx = current_idx
        best_ratio = -1.0
        for i in range(n):
            total = self._region_total[i]
            avail = self._region_avail[i]
            ratio = (avail / total) if total > 0 else 0.0
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = i
        if best_idx == current_idx:
            # Try the next region to diversify if best is current
            return (current_idx + 1) % n
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize tracking for regions
        self._init_region_stats_if_needed()

        # Update progress accumulator
        self._update_progress_accumulator()

        # Update region stats based on current observation
        try:
            curr_region = self.env.get_current_region()
        except Exception:
            curr_region = 0
        if self._region_total is not None and self._region_avail is not None:
            if 0 <= curr_region < len(self._region_total):
                self._region_total[curr_region] += 1
                if has_spot:
                    self._region_avail[curr_region] += 1

        # Compute remaining work and slack
        remaining_work = max(0.0, self.task_duration - self._accum_progress)
        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        slack = time_left - remaining_work

        # Safety margin to account for discretization/overheads. Commit a bit early.
        commit_threshold = overhead + max(gap * 2.0, 1.0)

        # If not yet committed, check whether we must switch to on-demand to guarantee finish.
        if not self._committed_on_demand:
            if slack <= commit_threshold:
                self._committed_on_demand = True

        # If committed to on-demand, keep running on-demand to finish.
        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        # Prefer Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available here: consider waiting (NONE) while safe, and rotate region to seek spot next step.
        # If waiting risks deadline, switch to on-demand.
        if slack > commit_threshold:
            # Try switching to the best-known region for the next step.
            try:
                best_region = self._select_best_region(curr_region)
                if best_region != curr_region:
                    self.env.switch_region(best_region)
            except Exception:
                pass
            return ClusterType.NONE

        # Not safe to wait any longer.
        self._committed_on_demand = True
        return ClusterType.ON_DEMAND