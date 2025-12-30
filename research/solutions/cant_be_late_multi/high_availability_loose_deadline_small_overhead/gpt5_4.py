import json
from argparse import Namespace
from math import ceil

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "risk_aware_rr"

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
        self._commit_to_on_demand = False
        self._num_regions = self.env.get_num_regions()
        self._region_obs = [0] * self._num_regions
        self._region_spot = [0] * self._num_regions

        return self

    def _od_time_needed_from_now(self, remaining_work: float, starting_on_od_now: bool) -> float:
        # Returns minimal elapsed time needed to finish using only On-Demand from this moment.
        step = self.env.gap_seconds
        if remaining_work <= 0:
            return 0.0
        if starting_on_od_now and self.env.cluster_type == ClusterType.ON_DEMAND:
            # Already on OD; no new overhead and full step capacity
            steps_total = ceil(remaining_work / step)
            return steps_total * step
        else:
            # Switching to OD (now or later): pay overhead, and first step loses overhead from compute capacity
            overhead = self.restart_overhead
            avail_first = max(0.0, step - overhead)
            if remaining_work <= avail_first:
                steps_total = 1
            else:
                rem_after_first = remaining_work - avail_first
                steps_total = 1 + ceil(rem_after_first / step)
            return overhead + steps_total * step

    def _update_region_stats(self, has_spot: bool):
        r = self.env.get_current_region()
        if 0 <= r < self._num_regions:
            self._region_obs[r] += 1
            if has_spot:
                self._region_spot[r] += 1

    def _choose_best_region(self) -> int:
        # Beta(1,1) prior; score = (succ+1)/(obs+2)
        best_idx = 0
        best_score = -1.0
        for i in range(self._num_regions):
            obs = self._region_obs[i]
            succ = self._region_spot[i]
            score = (succ + 1.0) / (obs + 2.0)
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _rotate_region(self):
        # Deterministic round-robin when scores tie or initially unknown
        current = self.env.get_current_region()
        if self._num_regions <= 1:
            return current
        next_region = (current + 1) % self._num_regions
        return next_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update region stats with current observation
        self._update_region_stats(has_spot)

        # If we've committed to On-Demand (to guarantee finish), stick with it.
        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Basic quantities
        step = self.env.gap_seconds
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(0.0, self.task_duration - work_done)
        time_left = self.deadline - self.env.elapsed_seconds

        # If no time left, best attempt is to run On-Demand
        if time_left <= 0:
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # If we have spot and the remaining work fits in one spot step, use Spot if it fits within deadline.
        if has_spot and remaining_work <= step:
            if time_left >= step:
                return ClusterType.SPOT
            # Not enough time to finish even with one step; choose OD as last resort
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Compute time needed if we start On-Demand now
        od_time_if_start_now = self._od_time_needed_from_now(remaining_work, starting_on_od_now=True)
        # Compute time needed if we start On-Demand next step
        od_time_if_start_next = self._od_time_needed_from_now(remaining_work, starting_on_od_now=False)

        # If the slack is already too tight to delay, immediately commit to On-Demand
        if time_left <= od_time_if_start_now:
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            # Check if we can afford to spend one step on Spot and still finish with OD afterward if needed.
            remaining_after_spot = max(0.0, remaining_work - step)
            od_time_after_spot = self._od_time_needed_from_now(remaining_after_spot, starting_on_od_now=False)
            time_left_after_step = time_left - step
            if time_left_after_step > od_time_after_spot:
                # Safe to use Spot this step
                return ClusterType.SPOT
            else:
                # Not safe; commit to On-Demand for the remainder
                self._commit_to_on_demand = True
                return ClusterType.ON_DEMAND
        else:
            # No Spot right now. Decide to wait (NONE) or switch to OD.
            time_left_after_wait = time_left - step
            if time_left_after_wait > od_time_if_start_next:
                # We can afford to wait one step to try Spot in another region.
                # Choose best region based on simple Bayesian estimate; if tie or unknown, rotate.
                best_region = self._choose_best_region()
                if best_region == self.env.get_current_region():
                    # If current already best (or all equal), do round-robin to explore
                    best_region = self._rotate_region()
                if 0 <= best_region < self._num_regions:
                    self.env.switch_region(best_region)
                return ClusterType.NONE
            else:
                # Not safe to wait; commit to On-Demand
                self._commit_to_on_demand = True
                return ClusterType.ON_DEMAND