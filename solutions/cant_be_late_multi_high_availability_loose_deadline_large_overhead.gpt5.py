import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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
        self._od_committed = False
        self._region_scores: Optional[List[float]] = None
        self._region_counts: Optional[List[int]] = None
        self._no_spot_streak: Optional[List[int]] = None
        self._last_switch_step = -10**9
        self._step_idx = 0

        # Params for heuristics
        self._score_alpha = 0.1  # EMA smoothing for region availability
        self._switch_cooldown_steps = 1  # avoid switching too frequently
        # Safety margin: one step plus a fraction of overhead
        self._safety_margin = (getattr(self.env, "gap_seconds", 3600.0)) + 0.5 * self.restart_overhead

        return self

    def _ensure_initialized(self):
        if self._initialized:
            return
        num_regions = self.env.get_num_regions()
        # Initialize with reasonably high belief because traces have high availability
        self._region_scores = [0.8 for _ in range(num_regions)]
        self._region_counts = [0 for _ in range(num_regions)]
        self._no_spot_streak = [0 for _ in range(num_regions)]
        self._initialized = True

    def _latest_od_start_time_left(self) -> float:
        # Time left in seconds when we must start OD to finish safely
        # Returns threshold time = remaining_work + OD start overhead (if not already on OD) + safety margin
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining = max(0.0, self.task_duration - done)
        od_start_overhead = 0.0 if self.env.cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return remaining + od_start_overhead + self._safety_margin

    def _update_region_stats(self, has_spot: bool):
        # Update EMA score for current region based on observed has_spot
        self._ensure_initialized()
        r = self.env.get_current_region()
        val = 1.0 if has_spot else 0.0
        # EMA update
        self._region_scores[r] = (1.0 - self._score_alpha) * self._region_scores[r] + self._score_alpha * val
        self._region_counts[r] += 1
        if has_spot:
            self._no_spot_streak[r] = 0
        else:
            self._no_spot_streak[r] += 1

    def _pick_best_region(self, avoid_idx: int) -> int:
        # Choose the best region based on highest EMA score; break ties by favoring next index
        self._ensure_initialized()
        scores = self._region_scores
        n = len(scores)
        best_idx = avoid_idx
        best_score = scores[avoid_idx]
        # Prefer another region only if it has a strictly higher score
        for i in range(n):
            if i == avoid_idx:
                continue
            s = scores[i]
            if s > best_score:
                best_score = s
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()
        self._step_idx += 1

        # If task already completed, ensure we don't run anything
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        if done >= self.task_duration - 1e-6:
            return ClusterType.NONE

        # Update region stats with current observation
        self._update_region_stats(has_spot)

        # Decide whether we must commit to On-Demand to meet deadline
        time_left = self.deadline - self.env.elapsed_seconds
        od_threshold = self._latest_od_start_time_left()
        if time_left <= od_threshold:
            self._od_committed = True

        # If committed to OD, always use OD to guarantee finishing
        if self._od_committed:
            return ClusterType.ON_DEMAND

        # Not yet committed: use SPOT if available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available in current region and we still have slack:
        # Consider switching to the best region for the next step
        current_region = self.env.get_current_region()
        if self._no_spot_streak[current_region] >= 1:
            if (self._step_idx - self._last_switch_step) >= self._switch_cooldown_steps:
                best_region = self._pick_best_region(current_region)
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    self._last_switch_step = self._step_idx

        # Wait this step to save cost; OD will be used later if needed by the commit rule
        return ClusterType.NONE
