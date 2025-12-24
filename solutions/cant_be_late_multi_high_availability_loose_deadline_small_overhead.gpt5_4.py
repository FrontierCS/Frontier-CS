import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_multi_region_v1"

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

        # Internal state init
        self._init_done = False
        self._od_committed = False
        self._beta_prior_a = 2.0
        self._beta_prior_b = 2.0
        self._switch_patience = 1  # steps of consecutive no-spot before switching on NONE
        self._switch_delta = 0.05  # required advantage to switch regions when waiting
        self._last_done_len = 0
        self._work_done_sum = 0.0
        self._od_buffer = None  # computed on first step based on gap and overhead
        return self

    # Initialize per-region stats lazily since env may not be ready during solve
    def _lazy_init(self):
        if self._init_done:
            return
        n = self.env.get_num_regions()
        self._obs_total: List[int] = [0] * n
        self._obs_spot: List[int] = [0] * n
        self._no_spot_streak: List[int] = [0] * n
        self._init_done = True
        if self._od_buffer is None:
            gap = float(self.env.gap_seconds)
            # Safety buffer before committing to On-Demand
            # Choose max of half step and restart overhead for robustness
            self._od_buffer = max(self.restart_overhead, 0.5 * gap)

    def _update_work_done_sum(self):
        l = len(self.task_done_time)
        if l > self._last_done_len:
            # Incrementally sum new segments
            for i in range(self._last_done_len, l):
                self._work_done_sum += float(self.task_done_time[i])
            self._last_done_len = l

    def _remaining_work(self) -> float:
        self._update_work_done_sum()
        remaining = self.task_duration - self._work_done_sum
        if remaining < 0.0:
            return 0.0
        return remaining

    def _update_region_stats(self, has_spot: bool):
        r = self.env.get_current_region()
        self._obs_total[r] += 1
        if has_spot:
            self._obs_spot[r] += 1
            self._no_spot_streak[r] = 0
        else:
            self._no_spot_streak[r] += 1

    def _best_region_index(self, current_idx: int) -> int:
        # Compute posterior mean of spot availability for each region with Beta prior
        best_idx = current_idx
        best_score = -1.0
        for i in range(self.env.get_num_regions()):
            a = self._beta_prior_a + self._obs_spot[i]
            b = self._beta_prior_b + (self._obs_total[i] - self._obs_spot[i])
            score = a / (a + b) if (a + b) > 0 else 0.5
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _maybe_switch_region_when_waiting(self, has_spot: bool):
        # Consider switching only when waiting (NONE will be chosen by caller)
        current = self.env.get_current_region()
        # Only switch if current region has been without spot for a bit
        if self._no_spot_streak[current] < self._switch_patience:
            return
        # Compute current score
        a_cur = self._beta_prior_a + self._obs_spot[current]
        b_cur = self._beta_prior_b + (self._obs_total[current] - self._obs_spot[current])
        score_cur = a_cur / (a_cur + b_cur) if (a_cur + b_cur) > 0 else 0.5
        # Select best region by score
        best = self._best_region_index(current)
        if best != current:
            a_best = self._beta_prior_a + self._obs_spot[best]
            b_best = self._beta_prior_b + (self._obs_total[best] - self._obs_spot[best])
            score_best = a_best / (a_best + b_best) if (a_best + b_best) > 0 else 0.5
            if score_best > score_cur + self._switch_delta:
                self.env.switch_region(best)

    def _must_commit_od(self, last_cluster_type: ClusterType) -> bool:
        # Determine if we must run OD to guarantee meeting the deadline
        now = float(self.env.elapsed_seconds)
        t_left = self.deadline - now
        if t_left <= 0.0:
            return True
        remaining = self._remaining_work()
        # If already on OD and staying, no new overhead
        overhead_if_switch = 0.0 if last_cluster_type == ClusterType.ON_DEMAND or self._od_committed else self.restart_overhead
        time_needed_od = remaining + overhead_if_switch
        return t_left <= (time_needed_od + self._od_buffer)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        # Update region statistics based on current observation
        self._update_region_stats(has_spot)

        # If we have already committed to OD, keep using OD until finish
        if self._od_committed:
            return ClusterType.ON_DEMAND

        commit_now = self._must_commit_od(last_cluster_type)

        if commit_now:
            # Commit to On-Demand, regardless of spot availability
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Not committing to OD yet
        if has_spot:
            # Use Spot when available
            return ClusterType.SPOT

        # Spot unavailable and not forced to OD yet: wait (NONE) and possibly switch region
        self._maybe_switch_region_when_waiting(has_spot)
        return ClusterType.NONE
