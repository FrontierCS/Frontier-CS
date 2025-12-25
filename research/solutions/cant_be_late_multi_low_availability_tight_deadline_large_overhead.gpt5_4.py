import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cb_late_multiregion_ema_v1"

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
        self._internal_initialized = False
        return self

    # -------- Internal helpers --------
    def _init_internal(self):
        if self._internal_initialized:
            return
        self._internal_initialized = True

        self._num_regions: int = max(1, int(self.env.get_num_regions()))
        self._region_scores: List[float] = [0.5 for _ in range(self._num_regions)]
        self._ema_alpha: float = 0.2

        self._rr_next: int = 0  # round-robin pointer for tie-breaking
        self._last_switch_elapsed: float = -1e18  # elapsed_seconds when we last switched
        self._switch_cooldown_seconds: float = self.env.gap_seconds  # avoid thrashing

        # Cached progress sum to avoid O(n^2) accumulation
        self._done_total: float = 0.0
        self._done_len: int = 0

        # Fallback to ON_DEMAND once threshold reached
        self._od_commit: bool = False

        # Safety buffers
        gap = float(self.env.gap_seconds)
        self._search_margin_time: float = self.restart_overhead + 2.0 * gap
        self._od_buffer_time: float = self.restart_overhead + 1.75 * gap

    def _update_done_total(self):
        if self._done_len != len(self.task_done_time):
            # Incremental sum to keep it efficient
            for i in range(self._done_len, len(self.task_done_time)):
                self._done_total += float(self.task_done_time[i])
            self._done_len = len(self.task_done_time)

    def _update_region_score(self, region_idx: int, has_spot: bool):
        # Exponential moving average update using current observation (has_spot) for this region
        s = self._region_scores[region_idx]
        observed = 1.0 if has_spot else 0.0
        self._region_scores[region_idx] = (1.0 - self._ema_alpha) * s + self._ema_alpha * observed

    def _best_alternative_region(self, current_idx: int) -> int:
        # Return the highest scored region different from current; break ties by round-robin preference
        n = self._num_regions
        if n <= 1:
            return current_idx
        # Sort indices by score descending; stable tie-breaker uses index order starting from rr pointer
        indices = list(range(n))
        # Rotate by round-robin pointer for consistent tie-breaking
        rr = self._rr_next % n
        rotated = indices[rr:] + indices[:rr]
        rotated_scores = sorted(rotated, key=lambda i: self._region_scores[i], reverse=True)
        for idx in rotated_scores:
            if idx != current_idx:
                return idx
        # Fallback to next in round-robin
        return (current_idx + 1) % n

    # -------- Core decision logic --------
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize internal state if needed
        self._init_internal()

        # Update cached progress
        self._update_done_total()

        # Compute essential quantities
        current_region = int(self.env.get_current_region())
        gap = float(self.env.gap_seconds)
        now = float(self.env.elapsed_seconds)
        total_needed = float(self.task_duration)
        done = self._done_total
        remaining_work = max(0.0, total_needed - done)
        time_left = max(0.0, float(self.deadline) - now)
        slack = time_left - remaining_work

        # If done, stop
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        # Update region score with current observation
        self._update_region_score(current_region, has_spot)

        # Determine if we must commit to On-Demand to guarantee completion
        # Use a conservative buffer to account for one restart and potential timestep boundary mismatch
        if not self._od_commit:
            if time_left <= remaining_work + self._od_buffer_time:
                self._od_commit = True

        # If committed to On-Demand, always run ON_DEMAND
        if self._od_commit:
            return ClusterType.ON_DEMAND

        # Prefer Spot when sufficiently safe
        if has_spot:
            return ClusterType.SPOT

        # No Spot available in current region.
        # Decide between searching other regions (by switching) vs using On-Demand vs waiting (NONE).
        # If slack is insufficient, use On-Demand to avoid missing deadline.
        if slack <= self._search_margin_time:
            return ClusterType.ON_DEMAND

        # We have enough slack to try searching for Spot in another region.
        # Avoid rapid thrashing: enforce a minimal cooldown between switches.
        if now - self._last_switch_elapsed >= self._switch_cooldown_seconds:
            target_region = self._best_alternative_region(current_region)
            if target_region != current_region:
                self.env.switch_region(target_region)
                self._last_switch_elapsed = now
                # advance round-robin pointer for future tie-breaking
                self._rr_next = (target_region + 1) % self._num_regions
                # Return NONE this step to avoid risking a SPOT action without guaranteed availability info.
                return ClusterType.NONE

        # If we recently switched or no better region exists, simply wait this step (NONE) if slack allows.
        # This avoids unnecessary On-Demand cost and gives time for Spot to reappear.
        return ClusterType.NONE
