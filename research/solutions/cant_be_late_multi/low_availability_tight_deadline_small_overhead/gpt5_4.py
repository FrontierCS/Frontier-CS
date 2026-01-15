import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._init_done = False
        self._n_regions = 0
        self._avail_score = []
        self._done_sum = 0.0
        self._prev_done_len = 0
        self._od_locked = False
        self._last_region = None

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
        return self

    def _lazy_init(self):
        if self._init_done:
            return
        try:
            self._n_regions = self.env.get_num_regions()
        except Exception:
            self._n_regions = 1
        if self._n_regions <= 0:
            self._n_regions = 1
        self._avail_score = [0.5 for _ in range(self._n_regions)]
        self._last_region = self.env.get_current_region() if hasattr(self, "env") else 0
        self._init_done = True

    def _update_done_sum(self):
        l = len(self.task_done_time)
        if l > self._prev_done_len:
            # Sum only the newly appended segments to keep O(1)/step
            inc = 0.0
            for i in range(self._prev_done_len, l):
                inc += self.task_done_time[i]
            self._done_sum += inc
            self._prev_done_len = l

    def _decide_region_switch_when_waiting(self, current_region: int):
        # Exponential decay for all regions towards 0.5 baseline to avoid stale beliefs
        # Small decay per step
        fade = 0.001
        base = 0.5
        for i in range(self._n_regions):
            self._avail_score[i] = self._avail_score[i] * (1.0 - fade) + base * fade

        # Choose the region with the highest score (not equal to current if possible)
        best_idx = current_region
        best_score = -1.0
        for i in range(self._n_regions):
            if i == current_region:
                continue
            if self._avail_score[i] > best_score:
                best_score = self._avail_score[i]
                best_idx = i
        if best_idx != current_region and 0 <= best_idx < self._n_regions:
            try:
                self.env.switch_region(best_idx)
                self._last_region = best_idx
            except Exception:
                pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Track which region we're currently in
        current_region = self.env.get_current_region()
        self._last_region = current_region

        # Update running sum of work done
        self._update_done_sum()

        # Update availability score for current region using exponential smoothing
        # Emphasize recent observation
        alpha = 0.02
        self._avail_score[current_region] = (
            (1.0 - alpha) * self._avail_score[current_region] + alpha * (1.0 if has_spot else 0.0)
        )

        # If preempted (spot to no spot), penalize current region slightly to react faster
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self._avail_score[current_region] *= 0.98

        # If task is already complete, do nothing
        remaining_work = max(0.0, self.task_duration - self._done_sum)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Sticky On-Demand policy: once we commit to OD, keep it to avoid extra overhead/risk
        if self._od_locked or last_cluster_type == ClusterType.ON_DEMAND:
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Compute time budget
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            # Out of time; best we can do is OD
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Overhead if we switch to On-Demand now
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_for_od_now = self.remaining_restart_overhead
        else:
            overhead_for_od_now = self.restart_overhead

        required_od_time_now = overhead_for_od_now + remaining_work
        slack = time_left - required_od_time_now

        # Minimum slack buffer to allow one more step of waiting or trying spot safely
        gap = self.env.gap_seconds
        buffer = gap

        # If we are at or below buffer slack, commit to OD to ensure on-time finish
        if slack <= buffer:
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot if available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: wait if we have buffer, and search other regions
        # Only wait if we still have more than one step of slack after waiting this step
        if slack > buffer:
            # Switch to a region with higher recent availability
            self._decide_region_switch_when_waiting(current_region)
            return ClusterType.NONE

        # Fallback: commit to On-Demand if unsure
        self._od_locked = True
        return ClusterType.ON_DEMAND