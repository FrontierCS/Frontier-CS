import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_multi_v1"

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
        n = self.env.get_num_regions()
        self._region_obs_count: List[int] = [0] * n
        self._region_spot_true_count: List[int] = [0] * n
        self._last_done_len: int = 0
        self._done_sum_seconds: float = 0.0
        self._last_switch_step: int = -10**9  # very negative
        self._step_counter: int = 0

        # Safety margins and thresholds (seconds)
        self._gap = float(self.env.gap_seconds)
        self._oh = float(self.restart_overhead)
        # Conservative margins to guarantee deadline
        self._margin_stop = max(self._gap, 2.0 * self._oh) + 0.5 * self._gap
        self._margin_resume = self._margin_stop + max(self._gap, self._oh)

        # Region selection smoothing prior probability for unseen regions
        self._prior_spot_prob = 0.85
        self._prior_weight = 4.0  # pseudo-counts

        # Do not aggressively switch regions too often while waiting
        self._min_steps_between_switches = 1

        return self

    def _update_done_sum(self):
        # Incremental sum to avoid O(n) summing at each step
        if len(self.task_done_time) > self._last_done_len:
            new_items = self.task_done_time[self._last_done_len :]
            self._done_sum_seconds += sum(new_items)
            self._last_done_len = len(self.task_done_time)

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        # Update simple counts for availability estimation
        self._region_obs_count[region_idx] += 1
        if has_spot:
            self._region_spot_true_count[region_idx] += 1

    def _best_region_to_try(self, current_region: int) -> int:
        # Choose region with highest estimated spot availability probability
        # Laplace-smoothed probability
        best_region = current_region
        best_score = -1.0
        for r in range(self.env.get_num_regions()):
            obs = self._region_obs_count[r]
            trues = self._region_spot_true_count[r]
            p = (trues + self._prior_weight * self._prior_spot_prob) / (
                obs + self._prior_weight
            )
            # Mild preference for staying in current region (reduce churn)
            if r == current_region:
                p += 1e-6
            if p > best_score:
                best_score = p
                best_region = r
        return best_region

    def _compute_slack(self, last_cluster_type: ClusterType, remaining_work: float, time_remaining: float) -> float:
        # Time to finish on On-Demand if we start/continue NOW without switching regions
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_needed = float(self.remaining_restart_overhead)
        else:
            overhead_needed = self._oh
        time_to_finish_on_od = remaining_work + overhead_needed
        slack = time_remaining - time_to_finish_on_od
        return slack

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._step_counter += 1

        # Update stats and progress
        current_region = self.env.get_current_region()
        self._update_region_stats(current_region, has_spot)
        self._update_done_sum()

        remaining_work = max(0.0, self.task_duration - self._done_sum_seconds)
        time_remaining = max(0.0, self.deadline - float(self.env.elapsed_seconds))

        # If already done, no need to run any further (the framework should stop, but be safe)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        slack = self._compute_slack(last_cluster_type, remaining_work, time_remaining)

        # If no time left or negative slack, must run On-Demand now to avoid missing deadline
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        # Near deadline safety: when slack is small, choose On-Demand to avoid risk
        if slack <= self._margin_stop:
            return ClusterType.ON_DEMAND

        # Plenty of slack: prefer Spot when available
        if has_spot:
            # Hysteresis: if we were on On-Demand, don't flip to Spot unless we have ample slack
            if last_cluster_type == ClusterType.ON_DEMAND and slack <= self._margin_resume:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot unavailable in current region.
        # If we have enough slack to wait for at least one full step (plus margin), we can wait.
        if slack > (self._gap + self._margin_stop):
            # While waiting, try switching to a region with better estimated availability.
            # Do not switch too frequently to avoid churn.
            next_region = self._best_region_to_try(current_region)
            if next_region != current_region and (self._step_counter - self._last_switch_step) >= self._min_steps_between_switches:
                self.env.switch_region(next_region)
                self._last_switch_step = self._step_counter
            return ClusterType.NONE

        # Not enough slack to wait: use On-Demand now
        return ClusterType.ON_DEMAND
