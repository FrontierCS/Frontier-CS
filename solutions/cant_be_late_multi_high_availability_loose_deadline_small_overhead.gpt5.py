import json
import math
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_multi_v3"

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

        # Strategy state
        self._initialized = False
        self._commit_to_od = False  # Once true, never switch back to spot
        self._num_regions = 1
        self._obs_counts: List[int] = []
        self._spot_counts: List[int] = []
        self._region_rr = 0  # round-robin pointer for tie-breaking
        self._prior_weight = 5.0
        self._prior_p = 0.9  # high prior availability; traces have high spot availability

        return self

    def _init_internal(self):
        if self._initialized:
            return
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1
        if self._num_regions <= 0:
            self._num_regions = 1
        self._obs_counts = [0] * self._num_regions
        self._spot_counts = [0] * self._num_regions
        # Start RR at current region to avoid immediate switch
        try:
            self._region_rr = int(self.env.get_current_region()) % self._num_regions
        except Exception:
            self._region_rr = 0
        self._initialized = True

    def _estimate_scores(self):
        # Bayesian mean estimate for each region's spot availability
        scores = []
        for i in range(self._num_regions):
            obs = self._obs_counts[i]
            spot = self._spot_counts[i]
            score = (spot + self._prior_weight * self._prior_p) / (obs + self._prior_weight)
            scores.append(score)
        return scores

    def _best_region(self, exclude_idx: int = -1) -> int:
        # Choose the region with highest estimated availability; tie-break by RR
        scores = self._estimate_scores()
        best_idx = None
        best_score = -1.0
        # Try two passes: start from RR pointer for mild load balancing
        start = self._region_rr % self._num_regions
        for offset in range(self._num_regions):
            i = (start + offset) % self._num_regions
            if i == exclude_idx and self._num_regions > 1:
                continue
            s = scores[i]
            if s > best_score:
                best_score = s
                best_idx = i
        if best_idx is None:
            best_idx = exclude_idx if exclude_idx >= 0 else 0
        return best_idx

    def _commit_threshold_time_needed(self, on_od_now: bool) -> float:
        # Compute conservative time needed to finish if we commit to OD.
        # Include one restart overhead if not already on OD.
        remaining_work = max(0.0, self.task_duration - sum(self.task_done_time))
        # If already on OD, consume any remaining restart overhead; otherwise, we will pay full restart overhead
        pending_overhead = 0.0
        if on_od_now:
            try:
                pending_overhead = getattr(self, "remaining_restart_overhead", 0.0)
            except Exception:
                pending_overhead = 0.0
        else:
            pending_overhead = self.restart_overhead
        # Add small discretization margin (gap) to be safe
        gap = getattr(self.env, "gap_seconds", 1.0)
        return remaining_work + pending_overhead + gap

    def _should_commit_to_od(self) -> bool:
        # Decide whether to switch to OD to guarantee finishing before deadline.
        # Commit if time left is less than or equal to the conservative time needed to finish on OD.
        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)
        on_od_now = (self.env.cluster_type == ClusterType.ON_DEMAND)
        needed = self._commit_threshold_time_needed(on_od_now)
        # Safety margin: include a fraction of restart overhead to hedge for edge rounding
        safety = 0.25 * self.restart_overhead
        return time_left <= (needed + safety)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_internal()

        # Prevent any surprise: if already committed to OD, always stay on OD
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Update region statistics
        try:
            current_region = int(self.env.get_current_region())
            if 0 <= current_region < self._num_regions:
                self._obs_counts[current_region] += 1
                if has_spot:
                    self._spot_counts[current_region] += 1
        except Exception:
            current_region = 0

        # If finishing soon, ensure no unnecessary work
        remaining_work = max(0.0, self.task_duration - sum(self.task_done_time))
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If we are close to the deadline, commit to OD
        if self._should_commit_to_od():
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # If spot is available now, use it
        if has_spot:
            return ClusterType.SPOT

        # Spot not available here; if we are very close to deadline, commit to OD
        if self._should_commit_to_od():
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Explore other regions by switching to the best estimated one and pause this step
        if self._num_regions > 1:
            best = self._best_region(exclude_idx=current_region)
            if best != current_region:
                try:
                    self.env.switch_region(best)
                except Exception:
                    pass
                # Update RR pointer for future tie-breaking
                self._region_rr = (best + 1) % self._num_regions
            else:
                self._region_rr = (self._region_rr + 1) % self._num_regions

        # Pause for this timestep to avoid OD cost; try again next step
        return ClusterType.NONE
