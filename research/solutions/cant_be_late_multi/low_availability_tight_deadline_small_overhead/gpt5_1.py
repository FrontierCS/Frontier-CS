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
        # Custom state
        self._init_done = False
        self._num_regions = 0
        self._p: List[float] = []  # EWMA availability per region
        self._obs_time: List[float] = []  # seconds observed in region
        self._streak: List[int] = []  # positive for spot streak, negative for no-spot streak
        self._last_seen_spot: List[int] = []  # 1 for spot seen last, 0 for no-spot last, -1 unknown
        self._alpha = 0.02  # EWMA smoothing
        self._base_prior = 0.3
        self._commit_to_od = False
        self._safety_buffer = None  # set at first step
        self._cum_done = 0.0
        self._last_done_len = 0
        return self

    def _ensure_init(self):
        if not self._init_done and self.env is not None:
            self._num_regions = self.env.get_num_regions()
            self._p = [self._base_prior for _ in range(self._num_regions)]
            self._obs_time = [0.0 for _ in range(self._num_regions)]
            self._streak = [0 for _ in range(self._num_regions)]
            self._last_seen_spot = [-1 for _ in range(self._num_regions)]
            # Safety buffer: at least 2 minutes, or 3x overhead, or 2 time steps
            gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
            self._safety_buffer = max(120.0, 3.0 * float(self.restart_overhead), 2.0 * gap)
            # Initialize work cache
            self._cum_done = sum(self.task_done_time) if hasattr(self, "task_done_time") else 0.0
            self._last_done_len = len(self.task_done_time) if hasattr(self, "task_done_time") else 0
            self._init_done = True

    def _update_work_cache(self):
        # Update cumulative work done efficiently
        if hasattr(self, "task_done_time"):
            curr_len = len(self.task_done_time)
            if curr_len > self._last_done_len:
                # sum only the new segments
                add = 0.0
                for i in range(self._last_done_len, curr_len):
                    add += self.task_done_time[i]
                self._cum_done += add
                self._last_done_len = curr_len

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        # Update EWMA, observation time, streaks for the region we are currently in
        if 0 <= region_idx < self._num_regions:
            obs_val = 1.0 if has_spot else 0.0
            self._p[region_idx] = self._alpha * obs_val + (1.0 - self._alpha) * self._p[region_idx]
            gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
            self._obs_time[region_idx] += gap
            last = self._last_seen_spot[region_idx]
            if has_spot:
                if last == 1:
                    self._streak[region_idx] += 1
                else:
                    self._streak[region_idx] = 1
                self._last_seen_spot[region_idx] = 1
            else:
                if last == 0:
                    self._streak[region_idx] -= 1
                else:
                    self._streak[region_idx] = -1
                self._last_seen_spot[region_idx] = 0

    def _score_region(self, idx: int) -> float:
        # Combine EWMA with streak to prefer persistent availability
        # cap streak influence to be small
        s = self._streak[idx]
        if s > 100:
            s = 100
        elif s < -100:
            s = -100
        # small weight for streak; small bonus for last seen spot
        streak_bonus = 0.002 * s  # max +/- 0.2
        last_bonus = 0.03 if self._last_seen_spot[idx] == 1 else 0.0
        return self._p[idx] + streak_bonus + last_bonus

    def _choose_region_when_no_spot(self, current_region: int):
        # Exploration during early phase: ensure each region gets observed some minimal time
        elapsed = float(self.env.elapsed_seconds)
        # Explore for up to 4 hours or until each region has at least 10 minutes observation
        explore_time_limit = min(4.0 * 3600.0, 0.15 * float(self.deadline))
        min_obs_needed = 10.0 * 60.0
        target_region = current_region

        # Find region with minimum observation time
        min_obs_time = min(self._obs_time) if self._obs_time else 0.0
        if elapsed < explore_time_limit or min_obs_time < min_obs_needed:
            # Choose the region with smallest observation time to explore
            best_idx = current_region
            best_val = self._obs_time[current_region] if self._obs_time else 0.0
            for r in range(self._num_regions):
                if self._obs_time[r] < best_val - 1e-9:
                    best_val = self._obs_time[r]
                    best_idx = r
            target_region = best_idx
        else:
            # Exploitation: choose region with highest score
            best_idx = current_region
            best_score = self._score_region(current_region)
            for r in range(self._num_regions):
                sc = self._score_region(r)
                if sc > best_score + 1e-12:
                    best_score = sc
                    best_idx = r
            target_region = best_idx

        if target_region != current_region:
            # Switch region for next step; avoid switching if we are about to commit to OD this step
            self.env.switch_region(target_region)

    def _remaining_work(self) -> float:
        # Ensure work cache is up to date
        self._update_work_cache()
        rem = float(self.task_duration) - float(self._cum_done)
        if rem < 0.0:
            rem = 0.0
        return rem

    def _compute_time_to_finish_on_demand_now(self, last_cluster_type: ClusterType) -> float:
        rem_work = self._remaining_work()
        # Include pending overhead if already on OD, else include a restart overhead to switch to OD
        if last_cluster_type == ClusterType.ON_DEMAND:
            pending = float(self.remaining_restart_overhead)
            return rem_work + pending
        else:
            return rem_work + float(self.restart_overhead)

    def _should_commit_to_od(self, last_cluster_type: ClusterType) -> bool:
        # Commit when time left is tight relative to guaranteed completion on OD
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        t_finish_od = self._compute_time_to_finish_on_demand_now(last_cluster_type)
        buffer_sec = float(self._safety_buffer)
        return time_left <= t_finish_od + buffer_sec

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize on first step
        self._ensure_init()

        # Update region stats based on observation
        current_region = self.env.get_current_region()
        self._update_region_stats(current_region, has_spot)

        # Update commit condition
        if not self._commit_to_od and self._should_commit_to_od(last_cluster_type):
            self._commit_to_od = True

        # If already committed to OD, just run OD
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Pre-commit logic
        # Prefer spot when available
        if has_spot:
            return ClusterType.SPOT

        # No spot in current region this step
        # Consider switching regions for future steps
        self._choose_region_when_no_spot(current_region)

        # Decide to wait (NONE) or run OD this step
        # If we still have sufficient slack beyond OD guaranteed finish, wait; otherwise run OD
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        t_finish_od = self._compute_time_to_finish_on_demand_now(last_cluster_type)
        slack_over_guarantee = time_left - (t_finish_od + float(self._safety_buffer))

        if slack_over_guarantee > getattr(self.env, "gap_seconds", 60.0):
            # Wait for spot, saving cost
            return ClusterType.NONE

        # If slack is tight but not committed (e.g., borderline), fallback to OD for safety
        return ClusterType.ON_DEMAND