import json
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_v1"

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

        # Runtime state (lazy init after env is ready in _step)
        self._initialized = False
        self.lock_od = False
        self.alpha_prior = 1.0
        self.beta_prior = 1.0
        self.safety_padding_seconds = 0.0
        self.region_avail = []
        self.region_obs = []
        return self

    def _lazy_init(self):
        if self._initialized:
            return
        n = self.env.get_num_regions()
        self.region_avail = [0] * n
        self.region_obs = [0] * n
        # Safety padding: account for discrete step and overhead rounding
        # Use a conservative buffer of ~1.5 steps + overhead + small constant
        self.safety_padding_seconds = (self.env.gap_seconds * 1.5) + self.restart_overhead + 30.0
        self._initialized = True

    def _spot_score(self, idx: int) -> float:
        # Beta posterior mean with simple prior
        return (self.region_avail[idx] + self.alpha_prior) / (
            self.region_obs[idx] + self.alpha_prior + self.beta_prior
        )

    def _best_region(self, current_idx: int) -> Optional[int]:
        # Choose region with highest estimated spot availability
        n = self.env.get_num_regions()
        best_idx = None
        best_score = -1.0
        for i in range(n):
            s = self._spot_score(i)
            if s > best_score:
                best_score = s
                best_idx = i
        # If best is current and we have no spot now, try next region to explore
        if best_idx == current_idx:
            if n > 1:
                return (current_idx + 1) % n
        return best_idx

    def _remaining_work_seconds(self) -> float:
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        return max(0.0, self.task_duration - done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Update availability statistics for the current region based on observation at this timestep.
        cur_region = self.env.get_current_region()
        self.region_obs[cur_region] += 1
        if has_spot:
            self.region_avail[cur_region] += 1

        remaining_work = self._remaining_work_seconds()
        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)

        # Compute OD time needed including overheads:
        if last_cluster_type == ClusterType.ON_DEMAND:
            # If already on OD, remaining restart overhead still needs to be consumed
            overhead_future = getattr(self, "remaining_restart_overhead", 0.0)
        else:
            # If switching to OD, we will incur one restart overhead (replacing any pending one)
            overhead_future = self.restart_overhead

        od_time_needed = remaining_work + overhead_future

        if self.lock_od:
            return ClusterType.ON_DEMAND

        # If we're at risk of missing the deadline, lock into On-Demand to guarantee completion.
        if time_left <= od_time_needed + self.safety_padding_seconds:
            self.lock_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available now; we have slack to wait or explore other regions.
        # Move to a promising region for the next step and wait this step to avoid costs.
        if self.env.get_num_regions() > 1:
            target = self._best_region(cur_region)
            if target is not None and target != cur_region:
                self.env.switch_region(target)

        return ClusterType.NONE