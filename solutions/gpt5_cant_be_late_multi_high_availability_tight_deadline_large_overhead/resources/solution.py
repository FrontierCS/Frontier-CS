import json
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

        # Internal state initialization
        self._initialized = False
        self._total_done = 0.0
        self._last_len = 0
        self._commit_to_od = False
        self._step_count = 0
        self._miss_streak = 0
        self._last_switch_step = -10**9
        self._alpha = 0.08  # smoothing factor for region spot availability score
        self._switch_threshold = 0.05  # minimum score improvement to justify switch
        self._max_switch_per_step = 1
        self._switches_this_step = 0
        return self

    def _lazy_init(self):
        if self._initialized:
            return
        # Initialize region tracking
        try:
            self._num_regions = self.env.get_num_regions()
        except Exception:
            self._num_regions = 1
        self._region_score = [0.5 for _ in range(self._num_regions)]
        self._region_total = [0 for _ in range(self._num_regions)]
        self._region_success = [0 for _ in range(self._num_regions)]
        self._initialized = True

    def _update_done_progress(self):
        # Incrementally track total work done to avoid repeated summation
        cur_len = len(self.task_done_time)
        if cur_len > self._last_len:
            # Usually only one new segment per step
            for i in range(self._last_len, cur_len):
                self._total_done += self.task_done_time[i]
            self._last_len = cur_len

    def _remaining_work(self):
        self._update_done_progress()
        rem = self.task_duration - self._total_done
        if rem < 0:
            rem = 0.0
        return rem

    def _should_commit_od(self, remaining_work, remaining_time):
        # Commit once running only On-Demand guarantees finish by deadline
        # Threshold: remaining_time <= remaining_work + restart_overhead + margin
        # margin ~ one step plus a bit for uncertainty
        X = float(self.env.gap_seconds)
        O = float(self.restart_overhead)
        margin = O + 1.2 * X
        return remaining_time <= (remaining_work + margin)

    def _pick_best_region(self, current_idx):
        # Choose region with highest score, but avoid switching if improvement is tiny
        best_idx = current_idx
        best_score = self._region_score[current_idx]
        for i in range(self._num_regions):
            s = self._region_score[i]
            if s > best_score + self._switch_threshold:
                best_score = s
                best_idx = i
        # If no significantly better region, consider round-robin after a few misses
        if best_idx == current_idx and self._miss_streak >= 1 and self._num_regions > 1:
            best_idx = (current_idx + 1) % self._num_regions
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._switches_this_step = 0
        self._step_count += 1

        # Update region score based on observed availability in current region
        try:
            cur_region = self.env.get_current_region()
        except Exception:
            cur_region = 0

        # smooth score update
        self._region_total[cur_region] += 1
        if has_spot:
            self._region_success[cur_region] += 1
        old = self._region_score[cur_region]
        self._region_score[cur_region] = old * (1.0 - self._alpha) + (1.0 if has_spot else 0.0) * self._alpha

        # Compute remaining work and remaining time
        remaining_work = self._remaining_work()
        remaining_time = float(self.deadline - self.env.elapsed_seconds)

        if remaining_work <= 0:
            return ClusterType.NONE

        # Commitment to On-Demand if time is tight
        if not self._commit_to_od and self._should_commit_od(remaining_work, remaining_time):
            self._commit_to_od = True

        if self._commit_to_od:
            # Once committed to OD, stick to it
            self._miss_streak = 0
            return ClusterType.ON_DEMAND

        # Not committed yet: prefer Spot when available
        if has_spot:
            self._miss_streak = 0
            return ClusterType.SPOT

        # Spot not available: consider switching region and/or waiting
        self._miss_streak += 1

        # If time is getting tighter (within two steps), proactively go OD
        X = float(self.env.gap_seconds)
        O = float(self.restart_overhead)
        if remaining_time <= remaining_work + O + 2.0 * X:
            # Not fully committed threshold, but close enough with spot missing: choose OD now
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Try switch to another region to improve chance of spot next step
        target_region = self._pick_best_region(cur_region)
        if target_region != cur_region and self._switches_this_step < self._max_switch_per_step:
            try:
                self.env.switch_region(target_region)
                self._last_switch_step = self._step_count
                self._switches_this_step += 1
            except Exception:
                pass

        # Wait this step (free) to try spot in a (possibly) better region next step
        return ClusterType.NONE
