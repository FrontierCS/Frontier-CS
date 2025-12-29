import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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

        # Internal state for efficiency and region selection
        self._initialized = False
        self._done_sum = 0.0
        self._prev_work_len = 0
        self._total_wait_seconds = 0.0
        self._region_scores: List[float] = []
        self._alpha = 0.08  # EMA update rate for region scores
        self._last_region = None
        return self

    def _init_once(self):
        if self._initialized:
            return
        n_regions = max(1, int(self.env.get_num_regions()))
        # Initialize region scores with a high prior since traces have high availability
        self._region_scores = [0.75] * n_regions
        self._initialized = True
        self._last_region = self.env.get_current_region()

    def _update_progress_cache(self):
        # Incremental sum to avoid O(n) sum every step
        cur_len = len(self.task_done_time)
        if cur_len > self._prev_work_len:
            self._done_sum += sum(self.task_done_time[self._prev_work_len:cur_len])
            self._prev_work_len = cur_len

    def _critical_buffer_seconds(self):
        # Buffer to guarantee completion on switching to On-Demand:
        # account for discrete step granularity and restart overheads.
        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)
        # Use a conservative buffer: 2 * gap + 3 * overhead (bounded minimum 30 minutes)
        return max(1800.0, 2.0 * gap + 3.0 * overhead)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_once()

        # Update region score for current region using current availability observation
        current_region = self.env.get_current_region()
        if 0 <= current_region < len(self._region_scores):
            # EMA update
            s = self._region_scores[current_region]
            self._region_scores[current_region] = (1.0 - self._alpha) * s + self._alpha * (1.0 if has_spot else 0.0)

        # Maintain progress cache
        self._update_progress_cache()

        # Basic variables in seconds
        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed
        remaining_work = float(self.task_duration) - self._done_sum

        # If already done or no time left, do nothing
        if remaining_work <= 0.0 or time_left <= 0.0:
            return ClusterType.NONE

        # Safety check: ensure we can finish with On-Demand if necessary
        crit_buf = self._critical_buffer_seconds()

        # If we are close to deadline, force On-Demand to guarantee completion
        if time_left <= remaining_work + crit_buf:
            return ClusterType.ON_DEMAND

        # Prefer SPOT whenever available and we're not at risk
        if has_spot:
            return ClusterType.SPOT

        # Spot not available at current region. Decide to wait (NONE) or use ON_DEMAND.
        # Slack = spare time relative to required remaining work
        slack = time_left - remaining_work

        # If there is enough slack beyond critical buffer, we can afford to wait for spot
        if slack > crit_buf:
            # As we choose to wait, optionally switch to a better region (for next step)
            n_regions = len(self._region_scores)
            if n_regions > 1:
                # Choose region with highest EMA score
                best_idx = max(range(n_regions), key=lambda i: self._region_scores[i])
                # Only switch if the best region is not current and has a sufficiently higher score
                if best_idx != current_region:
                    # Mild threshold to avoid thrash; switch if better by small margin
                    if self._region_scores[best_idx] >= self._region_scores[current_region] + 0.02:
                        self.env.switch_region(best_idx)
            # Wait to conserve budget, given we have slack
            return ClusterType.NONE

        # Slack is not enough to wait: use On-Demand
        return ClusterType.ON_DEMAND