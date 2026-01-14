import json
import math
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "smart_robust_wait_od"

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
        self._progress_seconds = 0.0
        self._last_done_len = 0
        self._commit_on_demand = False
        self._initialized_regions = False
        self._region_seen: List[int] = []
        self._region_avail: List[int] = []
        self._alpha_prior = 1.0
        self._beta_prior = 1.0

        return self

    def _init_regions_if_needed(self):
        if not self._initialized_regions:
            n = self.env.get_num_regions()
            self._region_seen = [0] * n
            self._region_avail = [0] * n
            self._initialized_regions = True

    def _update_progress_cache(self):
        if self._last_done_len != len(self.task_done_time):
            # sum only new entries to keep O(1) amortized
            added = 0.0
            for v in self.task_done_time[self._last_done_len :]:
                added += v
            self._progress_seconds += added
            self._last_done_len = len(self.task_done_time)

    def _od_wall_time_upperbound(self, remaining: float) -> float:
        if remaining <= 0:
            return 0.0
        G = self.env.gap_seconds
        O = self.restart_overhead
        first_cap = max(0.0, min(G, remaining) - O)
        rem_after_first = remaining - first_cap
        if rem_after_first <= 0:
            steps = 1
        else:
            steps = 1 + int(math.ceil(rem_after_first / G))
        return steps * G

    def _choose_region_when_waiting(self, current_region: int) -> int:
        # Choose region with highest estimated availability probability
        # p_hat = (avail + alpha) / (seen + alpha + beta)
        # Break ties with lower index preference
        best_region = current_region
        best_score = -1.0
        n = len(self._region_seen)
        for r in range(n):
            seen = self._region_seen[r]
            avail = self._region_avail[r]
            score = (avail + self._alpha_prior) / (seen + self._alpha_prior + self._beta_prior)
            if score > best_score:
                best_score = score
                best_region = r
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_regions_if_needed()
        self._update_progress_cache()

        # Update region availability stats with the observation at this timestep for the current region.
        curr_region = self.env.get_current_region()
        if 0 <= curr_region < len(self._region_seen):
            self._region_seen[curr_region] += 1
            if has_spot:
                self._region_avail[curr_region] += 1

        # If already finished, idle.
        remaining = max(0.0, self.task_duration - self._progress_seconds)
        if remaining <= 0.0:
            return ClusterType.NONE

        # Time computations
        slack = max(0.0, self.deadline - self.env.elapsed_seconds)
        G = self.env.gap_seconds

        # Upper bound on time needed to finish with on-demand from now if we switch immediately.
        od_time_needed = self._od_wall_time_upperbound(remaining)

        # Commit to on-demand if we are at or inside the required time window.
        if not self._commit_on_demand and slack <= od_time_needed:
            self._commit_on_demand = True

        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        # Not yet committed to on-demand:
        # Prefer SPOT if available; else choose to wait (NONE) if we have enough slack to lose one step,
        # otherwise switch to ON_DEMAND.
        if has_spot:
            return ClusterType.SPOT

        # SPOT not available here: decide to wait (NONE) and switch to a better region if we have buffer >= one step
        if slack >= od_time_needed + G:
            # Move to a region with higher estimated spot availability before idling
            target_region = self._choose_region_when_waiting(curr_region)
            if target_region != curr_region:
                self.env.switch_region(target_region)
            return ClusterType.NONE

        # Not enough slack to wait: switch to ON_DEMAND now to guarantee completion
        self._commit_on_demand = True
        return ClusterType.ON_DEMAND