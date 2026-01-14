import json
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

        # Internal state
        self._num_regions = self.env.get_num_regions()
        self._commit_to_od = False
        self._commit_fudge_seconds = max(2.0 * self.env.gap_seconds + self.restart_overhead, self.env.gap_seconds)
        self._done_sum_seconds = 0.0
        self._done_list_idx = 0

        # Region rotation and simple learned availability score (EWMA)
        self._region_scores = [0.5] * self._num_regions
        self._score_alpha = 0.15  # EWMA update rate
        self._rr_order = list(range(self._num_regions))
        self._last_region_checked = self.env.get_current_region()

        return self

    def _update_progress_cache(self):
        # Incremental sum of task_done_time to avoid O(n) per step
        if self._done_list_idx < len(self.task_done_time):
            for seg in self.task_done_time[self._done_list_idx:]:
                self._done_sum_seconds += float(seg)
            self._done_list_idx = len(self.task_done_time)

    def _should_commit_to_on_demand(self, last_cluster_type: ClusterType, remaining_work: float) -> bool:
        if self._commit_to_od:
            return True
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            return True
        od_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return time_left <= (remaining_work + od_overhead + self._commit_fudge_seconds)

    def _update_region_score(self, region_idx: int, has_spot: bool):
        # EWMA score update for the region we are currently in
        alpha = self._score_alpha
        prev = self._region_scores[region_idx]
        obs = 1.0 if has_spot else 0.0
        self._region_scores[region_idx] = (1 - alpha) * prev + alpha * obs

    def _choose_best_region(self, exclude_idx: int) -> int:
        # Choose region with highest score (ties -> lowest index), excluding current
        best_idx = exclude_idx
        best_score = -1.0
        for i, s in enumerate(self._region_scores):
            if i == exclude_idx:
                continue
            if s > best_score:
                best_score = s
                best_idx = i
        # If all excluded or equivalent, do simple round-robin to explore
        if best_idx == exclude_idx:
            best_idx = (exclude_idx + 1) % self._num_regions
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update progress
        self._update_progress_cache()
        remaining_work = max(0.0, self.task_duration - self._done_sum_seconds)

        # If task done, do nothing
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        current_region = self.env.get_current_region()

        # Update observed score for current region
        self._update_region_score(current_region, has_spot)

        # Decide whether to commit to On-Demand to guarantee deadline
        if self._should_commit_to_on_demand(last_cluster_type, remaining_work):
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Not committed to OD yet; prefer SPOT if available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available here; attempt to switch to a more promising region and wait
        # Switching now influences next step; returning NONE incurs no cost
        if self._num_regions > 1:
            next_region = self._choose_best_region(current_region)
            if next_region != current_region:
                self.env.switch_region(next_region)
        return ClusterType.NONE