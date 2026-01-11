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

        # Initialize internal state
        self._commit_on_demand = False
        self._last_work_done = 0.0
        self._alpha_prior = 1.0
        self._beta_prior = 1.0
        self._last_switch_target = None

        num_regions = self.env.get_num_regions()
        self._region_avail: List[int] = [0 for _ in range(num_regions)]
        self._region_total: List[int] = [0 for _ in range(num_regions)]
        self._visited_steps: List[int] = [0 for _ in range(num_regions)]
        return self

    def _choose_best_region_to_try(self) -> int:
        n = self.env.get_num_regions()
        current = self.env.get_current_region()

        # Compute smoothed availability score
        scores = []
        for i in range(n):
            avail = self._region_avail[i]
            total = self._region_total[i]
            score = (avail + self._alpha_prior) / (total + self._alpha_prior + self._beta_prior)
            # Light recency boost for regions we have recently seen good availability
            scores.append((score, i))

        # Sort descending by score
        scores.sort(key=lambda x: (-x[0], x[1]))

        # Prefer a region different from current; avoid immediate repeat to the same failed target if possible.
        for _, idx in scores:
            if idx != current and idx != self._last_switch_target:
                self._last_switch_target = idx
                return idx

        # Fallbacks: if all else fails, choose next region round-robin
        idx = (current + 1) % n
        self._last_switch_target = idx
        return idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already done, don't run anything.
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        if work_remaining <= 0:
            self._commit_on_demand = False
            return ClusterType.NONE

        now = self.env.elapsed_seconds
        time_left = self.deadline - now
        gap = self.env.gap_seconds

        # Update per-region availability stats from observation at current region
        current_region = self.env.get_current_region()
        if 0 <= current_region < self.env.get_num_regions():
            self._region_total[current_region] += 1
            if has_spot:
                self._region_avail[current_region] += 1

        # If we have already committed to on-demand, keep running it to guarantee finish.
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        # Compute minimum time to finish if we start On-Demand now (includes restart overhead)
        # Use conservative full overhead on switch.
        time_needed_if_od_now = self.restart_overhead + work_remaining

        # If waiting one more step would make OD insufficient to meet deadline, start OD now.
        if now + gap + time_needed_if_od_now > self.deadline:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available in the current region.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available in current region; assess slack and decide to search/wait or start OD.
        slack_after_od = time_left - time_needed_if_od_now
        if slack_after_od <= 0:
            # No slack left; must start OD now.
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # There is slack to wait/search. Try switching to the most promising region and wait this step.
        target = self._choose_best_region_to_try()
        if target != current_region:
            self.env.switch_region(target)

        # Wait one step to observe availability in the new region (or same region if no better choice).
        return ClusterType.NONE