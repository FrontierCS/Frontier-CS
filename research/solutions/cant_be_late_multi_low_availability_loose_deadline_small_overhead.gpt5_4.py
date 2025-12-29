import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_v2"

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
        self._initialized_internal = False
        self.od_committed = False
        self.work_sum = 0.0
        self.work_len = 0
        self.step_counter = 0
        return self

    def _init_internal(self):
        # Initialize lazy attributes depending on env
        self.num_regions = max(1, int(self.env.get_num_regions()))
        self.region_seen = [0] * self.num_regions
        self.region_spot = [0] * self.num_regions
        self.no_spot_streak = [0] * self.num_regions

        gap = float(self.env.gap_seconds)
        self.restart_overhead = float(self.restart_overhead)
        # Commit margin: be conservative to avoid deadline miss due to discretization
        self.od_commit_margin = max(gap, self.restart_overhead)

        # Switching heuristics
        switch_threshold_seconds = 600.0  # time without spot before considering switch (~10 minutes)
        cooldown_seconds = 300.0  # cooldown after a switch (~5 minutes)
        self.switch_threshold_steps = max(1, int(math.ceil(switch_threshold_seconds / gap)))
        self.switch_cooldown_steps = max(1, int(math.ceil(cooldown_seconds / gap)))
        self.last_switch_step = -10**9
        self.switch_eps = 0.03  # minimum improvement in estimated availability to switch

        # Prior for availability estimation (Beta prior)
        self.prior_alpha = 2.0
        self.prior_beta = 3.0

        self._initialized_internal = True

    def _update_progress_sum(self):
        # Incrementally update total productive work sum
        cur_len = len(self.task_done_time)
        if cur_len > self.work_len:
            for i in range(self.work_len, cur_len):
                self.work_sum += self.task_done_time[i]
            self.work_len = cur_len

    def _best_region(self, current_idx: int) -> int:
        # Choose region with highest estimated availability
        best_idx = current_idx
        best_score = -1.0
        for r in range(self.num_regions):
            seen = self.region_seen[r]
            spot = self.region_spot[r]
            score = (self.prior_alpha + spot) / (self.prior_alpha + self.prior_beta + seen)
            if score > best_score:
                best_score = score
                best_idx = r
        return best_idx

    def _should_switch_region(self, current_idx: int, time_left: float, rem: float) -> bool:
        # Decide whether to switch regions when spot unavailable
        if self.num_regions <= 1:
            return False
        if (self.step_counter - self.last_switch_step) < self.switch_cooldown_steps:
            return False
        # Only consider switching if we have enough slack for at least one idle step
        # beyond the OD minimum start time
        slack_after_one_step = time_left - self.env.gap_seconds - (rem + self.restart_overhead + self.od_commit_margin)
        if slack_after_one_step <= 0:
            return False
        # Require enough consecutive no-spot steps to consider switching
        if self.no_spot_streak[current_idx] < self.switch_threshold_steps:
            return False

        # Only switch if another region looks notably better
        cur_seen = self.region_seen[current_idx]
        cur_spot = self.region_spot[current_idx]
        cur_score = (self.prior_alpha + cur_spot) / (self.prior_alpha + self.prior_beta + cur_seen)
        best_idx = self._best_region(current_idx)
        if best_idx != current_idx:
            best_seen = self.region_seen[best_idx]
            best_spot = self.region_spot[best_idx]
            best_score = (self.prior_alpha + best_spot) / (self.prior_alpha + self.prior_beta + best_seen)
            if best_score >= cur_score + self.switch_eps:
                return True
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized_internal:
            self._init_internal()

        self.step_counter += 1
        self._update_progress_sum()

        # Remaining work and time
        rem = max(0.0, float(self.task_duration) - self.work_sum)
        if rem <= 0.0:
            return ClusterType.NONE

        t = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - t
        if time_left <= 0:
            # Best effort fallback
            self.od_committed = True
            return ClusterType.ON_DEMAND

        current_region = int(self.env.get_current_region())

        # Update region stats
        self.region_seen[current_region] += 1
        if has_spot:
            self.region_spot[current_region] += 1
            self.no_spot_streak[current_region] = 0
        else:
            self.no_spot_streak[current_region] += 1

        # Determine if we must commit to on-demand to guarantee finish
        overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        if not self.od_committed:
            if time_left <= rem + overhead_to_od + self.od_commit_margin:
                self.od_committed = True

        if self.od_committed:
            return ClusterType.ON_DEMAND

        # Prefer spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: optionally switch region if it helps and slack allows
        if self._should_switch_region(current_region, time_left, rem):
            target = self._best_region(current_region)
            if target != current_region:
                self.env.switch_region(target)
                self.last_switch_step = self.step_counter

        # Wait (NONE) to save cost while we have slack; will commit to OD automatically later
        return ClusterType.NONE