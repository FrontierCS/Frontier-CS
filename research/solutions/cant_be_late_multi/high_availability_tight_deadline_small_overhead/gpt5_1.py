import json
from argparse import Namespace
from typing import List

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
        self._initialized = False
        self._commit_to_ondemand = False
        self._last_task_done_len = 0
        self._done_so_far = 0.0
        self._num_regions = 0
        self._rr_counter = 0
        self._region_up_counts: List[int] = []
        self._region_down_counts: List[int] = []
        self._region_scores: List[float] = []
        return self

    def _init_if_needed(self):
        if self._initialized:
            return
        self._initialized = True
        self._num_regions = self.env.get_num_regions()
        if self._num_regions <= 0:
            self._num_regions = 1
        self._rr_counter = self.env.get_current_region() % self._num_regions
        self._region_up_counts = [0 for _ in range(self._num_regions)]
        self._region_down_counts = [0 for _ in range(self._num_regions)]
        self._region_scores = [0.0 for _ in range(self._num_regions)]
        self._last_task_done_len = 0
        self._done_so_far = 0.0
        self._commit_to_ondemand = False

    def _update_progress(self):
        segs = self.task_done_time
        if len(segs) > self._last_task_done_len:
            # Sum only new segments
            new_sum = 0.0
            for i in range(self._last_task_done_len, len(segs)):
                new_sum += segs[i]
            self._done_so_far += new_sum
            self._last_task_done_len = len(segs)

    def _safe_to_idle_one_step(self, remaining_work: float) -> bool:
        # After idling one step, can we still finish by starting on-demand?
        # We assume starting on-demand after idle incurs one restart_overhead.
        return (self.env.elapsed_seconds
                + self.env.gap_seconds
                + self.restart_overhead
                + remaining_work) <= self.deadline

    def _should_commit_now(self, last_cluster_type: ClusterType, remaining_work: float) -> bool:
        # If starting/continuing on-demand right now, do we still make the deadline?
        # If last_cluster_type is already ON_DEMAND, no new overhead; else, overhead applied.
        overhead_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return (self.env.elapsed_seconds + overhead_now + remaining_work) > self.deadline

    def _choose_next_region(self, current_idx: int) -> int:
        # Prefer the region with the highest score; break ties by round-robin to ensure exploration.
        if self._num_regions <= 1:
            return current_idx
        best_idx = current_idx
        best_score = float("-inf")
        # Simple selection: consider all regions except current
        for offset in range(1, self._num_regions + 1):
            idx = (current_idx + offset) % self._num_regions
            score = self._region_scores[idx]
            # Add tiny bias based on round-robin counter to diversify choices
            bias = 1e-6 * ((self._rr_counter + idx) % self._num_regions)
            s = score + bias
            if s > best_score:
                best_score = s
                best_idx = idx
        # If all scores equal (e.g., at start), fall back to round-robin
        if best_score == float("-inf"):
            best_idx = (current_idx + 1) % self._num_regions
        return best_idx

    def _update_region_stats(self, has_spot: bool):
        idx = self.env.get_current_region()
        if has_spot:
            self._region_up_counts[idx] += 1
            # Reward availability
            self._region_scores[idx] += 1.0
        else:
            self._region_down_counts[idx] += 1
            # Penalize unavailability a bit stronger to adapt quickly
            self._region_scores[idx] -= 1.2
        # Keep scores bounded to prevent overflow
        if self._region_scores[idx] > 1000.0:
            self._region_scores[idx] = 1000.0
        elif self._region_scores[idx] < -1000.0:
            self._region_scores[idx] = -1000.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()
        self._update_progress()
        self._update_region_stats(has_spot)

        remaining_work = max(self.task_duration - self._done_so_far, 0.0)
        if remaining_work <= 0:
            return ClusterType.NONE

        # If we've already committed to on-demand, stay on it to avoid thrashing.
        if self._commit_to_ondemand:
            return ClusterType.ON_DEMAND

        # If even starting on-demand right now would miss the deadline (should be rare), just start now anyway.
        # This acts as a safeguard; the environment settings should prevent this usually.
        if self._should_commit_now(last_cluster_type, remaining_work):
            self._commit_to_ondemand = True
            return ClusterType.ON_DEMAND

        # Prefer running on Spot whenever available; safe because it reduces remaining work and does not worsen
        # the feasibility of switching to On-Demand later.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable in current region: decide to wait (NONE) and switch region, or commit to On-Demand now.
        if self._safe_to_idle_one_step(remaining_work):
            # We can afford to idle one step.
            current_idx = self.env.get_current_region()
            next_idx = self._choose_next_region(current_idx)
            if next_idx != current_idx:
                self.env.switch_region(next_idx)
                self._rr_counter = (self._rr_counter + 1) % self._num_regions
            return ClusterType.NONE
        else:
            # Can't afford to waste a step waiting; commit to On-Demand to ensure deadline.
            self._commit_to_ondemand = True
            return ClusterType.ON_DEMAND