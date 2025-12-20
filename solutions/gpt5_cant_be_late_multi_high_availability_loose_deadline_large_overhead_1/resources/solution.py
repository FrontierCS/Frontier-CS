import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cb_mr_strategy_v2"

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
        self._num_regions: int = self.env.get_num_regions()
        self._obs_total: List[int] = [0] * self._num_regions
        self._obs_avail: List[int] = [0] * self._num_regions

        # Running sum of completed work to avoid summing the list every step
        self._done_sum: float = 0.0
        self._last_td_len: int = 0

        # Time buffers (seconds)
        gap = self.env.gap_seconds
        self._panic_buffer: float = 2.0 * gap + self.restart_overhead
        self._dropback_buffer: float = 4.0 * gap + 2.0 * self.restart_overhead

        # Round robin pointer
        self._rr_next: int = (self.env.get_current_region() + 1) % max(1, self._num_regions)

        return self

    def _update_done_sum(self):
        if len(self.task_done_time) > self._last_td_len:
            # Incrementally add new segments
            for i in range(self._last_td_len, len(self.task_done_time)):
                self._done_sum += self.task_done_time[i]
            self._last_td_len = len(self.task_done_time)

    def _choose_next_region(self, current_idx: int) -> int:
        if self._num_regions <= 1:
            return current_idx
        # If we have no observations, use round-robin
        total_obs = sum(self._obs_total)
        if total_obs == 0:
            idx = self._rr_next
            self._rr_next = (self._rr_next + 1) % self._num_regions
            if idx == current_idx:
                idx = (idx + 1) % self._num_regions
                self._rr_next = (idx + 1) % self._num_regions
            return idx

        # Otherwise choose region with best smoothed availability
        best_idx = None
        best_score = -1.0
        for i in range(self._num_regions):
            if i == current_idx:
                continue
            tot = self._obs_total[i]
            avail = self._obs_avail[i]
            # Laplace smoothing
            score = (avail + 1.0) / (tot + 2.0)
            if score > best_score:
                best_score = score
                best_idx = i
        if best_idx is None:
            best_idx = (current_idx + 1) % self._num_regions
        return best_idx

    def _should_panic_to_od(self, last_cluster_type: ClusterType) -> bool:
        self._update_done_sum()
        time_left = self.deadline - self.env.elapsed_seconds
        work_remaining = max(0.0, self.task_duration - self._done_sum)
        overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return time_left <= work_remaining + overhead_to_od + self._panic_buffer

    def _can_dropback_to_spot(self) -> bool:
        # Determine if it's safe enough to leave On-Demand and go back to Spot.
        self._update_done_sum()
        time_left = self.deadline - self.env.elapsed_seconds
        work_remaining = max(0.0, self.task_duration - self._done_sum)
        # If we switch away from OD, a future OD fallback would incur overhead again.
        slack = time_left - (work_remaining + self.restart_overhead)
        return slack >= self._dropback_buffer

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update region observations
        cur_region = self.env.get_current_region()
        if cur_region < self._num_regions:
            self._obs_total[cur_region] += 1
            if has_spot:
                self._obs_avail[cur_region] += 1

        # If task is done, no need to run more
        self._update_done_sum()
        if self._done_sum >= self.task_duration:
            return ClusterType.NONE

        # If we must panic to On-Demand to be safe
        if self._should_panic_to_od(last_cluster_type):
            return ClusterType.ON_DEMAND

        # If we are on On-Demand but it's safe to drop back to Spot and Spot is available
        if last_cluster_type == ClusterType.ON_DEMAND and has_spot and self._can_dropback_to_spot():
            return ClusterType.SPOT

        # Prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot is not available now; try another region and wait (no cost) if it's safe
        next_region = self._choose_next_region(cur_region)
        if next_region != cur_region:
            self.env.switch_region(next_region)
        return ClusterType.NONE
