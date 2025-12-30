import json
import random
from argparse import Namespace

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

        # Internal state for efficiency and region learning
        self._done_sum_seconds = 0.0
        self._last_task_len = 0
        self._commit_on_demand = False

        self._rng = random.Random(42)
        self._ema_alpha = 0.2
        self._switch_epsilon = 0.02
        self._deadline_margin_seconds = 0.0

        n = self.env.get_num_regions()
        self._reg_score = [0.5 for _ in range(n)]
        self._no_spot_streak = 0
        self._rotate_interval = 6  # rotate every N consecutive no-spot observations

        return self

    def _update_work_done_sum(self):
        # Incrementally track total work done to avoid summing the whole list each step
        cur_len = len(self.task_done_time)
        if cur_len > self._last_task_len:
            # Sum only the new segments
            added = 0.0
            for v in self.task_done_time[self._last_task_len:cur_len]:
                added += v
            self._done_sum_seconds += added
            self._last_task_len = cur_len

    def _best_region_by_score(self, cur_region: int) -> int:
        # Choose the region with the highest EMA score; break ties by index
        best_idx = cur_region
        best_score = self._reg_score[cur_region]
        for i, s in enumerate(self._reg_score):
            if s > best_score + 1e-12:
                best_score = s
                best_idx = i
        return best_idx

    def _should_commit_to_ondemand(self, last_cluster_type: ClusterType) -> bool:
        # Compute if we must switch to on-demand now to guarantee meeting deadline
        remaining_work = max(self.task_duration - self._done_sum_seconds, 0.0)
        slack = self.deadline - self.env.elapsed_seconds

        if remaining_work <= 0:
            return False

        # Overhead if we switch now; if already on-demand, overhead is zero
        overhead_if_switch = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead

        needed = remaining_work + overhead_if_switch + self._deadline_margin_seconds
        return slack <= needed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update region availability estimate for current region
        cur_region = self.env.get_current_region()
        # Exponential moving average update with observation
        obs = 1.0 if has_spot else 0.0
        self._reg_score[cur_region] = (1.0 - self._ema_alpha) * self._reg_score[cur_region] + self._ema_alpha * obs

        # Track work done efficiently
        self._update_work_done_sum()
        remaining_work = max(self.task_duration - self._done_sum_seconds, 0.0)

        # If already done, stop running anything
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Decide if we must commit to on-demand to guarantee completion
        if not self._commit_on_demand and self._should_commit_to_ondemand(last_cluster_type):
            self._commit_on_demand = True

        if self._commit_on_demand:
            # Once committed, stick with On-Demand to avoid extra overheads
            return ClusterType.ON_DEMAND

        # Not committed: prefer Spot when available; otherwise, wait (NONE) and reposition region if beneficial
        if has_spot:
            # Continue on spot; avoid region switching while spot is available this step
            self._no_spot_streak = 0
            return ClusterType.SPOT

        # Spot not available this step; consider switching region for next step
        self._no_spot_streak += 1

        best_idx = self._best_region_by_score(cur_region)
        # Switch if the best region's score is meaningfully better than current
        if best_idx != cur_region and self._reg_score[best_idx] > self._reg_score[cur_region] + self._switch_epsilon:
            self.env.switch_region(best_idx)
        else:
            # If scores are similar and we've been dry for many steps, rotate to explore
            if self._no_spot_streak % self._rotate_interval == 0:
                n = self.env.get_num_regions()
                if n > 1:
                    self.env.switch_region((cur_region + 1) % n)

        return ClusterType.NONE