import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cb_late_rr_v1"

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
        self._done_sum = 0.0
        self._last_done_len = 0
        self._committed_od = False
        try:
            num_r = self.env.get_num_regions()
        except Exception:
            num_r = 1
        try:
            cur = self.env.get_current_region()
        except Exception:
            cur = 0
        self._rr_next = (cur + 1) % max(num_r, 1)
        return self

    def _update_progress_sum(self):
        # Incrementally update the sum of task_done_time to avoid O(n) per step
        curr_len = len(self.task_done_time)
        if curr_len > self._last_done_len:
            # Usually only one element appended per step
            for i in range(self._last_done_len, curr_len):
                self._done_sum += float(self.task_done_time[i])
            self._last_done_len = curr_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update progress tracking
        self._update_progress_sum()

        # Remaining work and time
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        remaining_work = max(self.task_duration - self._done_sum, 0.0)
        time_left = max(self.deadline - self.env.elapsed_seconds, 0.0)

        # If already done, idle
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Commit buffer to account for discretization/rounding; small compared to overhead
        commit_buffer = min(gap, 60.0)
        commit_threshold = self.restart_overhead + commit_buffer

        # If we've already committed to on-demand, keep using it
        if self._committed_od:
            return ClusterType.ON_DEMAND

        # If already on ON_DEMAND (shouldn't be without commit), stick to it to avoid thrash
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # If time is very tight, commit to ON_DEMAND to guarantee finish
        slack = time_left - remaining_work
        if slack <= commit_threshold or time_left <= 0.0:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available and we have sufficient slack
        if has_spot:
            return ClusterType.SPOT

        # SPOT not available: decide to wait (NONE) or commit to ON_DEMAND
        allowed_wait = slack - commit_threshold

        if allowed_wait > gap * 0.99:
            # We can afford to wait this step: try another region (round-robin) to find spot
            try:
                num_r = self.env.get_num_regions()
            except Exception:
                num_r = 1
            if num_r and num_r > 1:
                curr = self.env.get_current_region()
                # Ensure we don't keep setting to same region
                if self._rr_next == curr:
                    self._rr_next = (curr + 1) % num_r
                self.env.switch_region(self._rr_next)
                self._rr_next = (self._rr_next + 1) % num_r
            return ClusterType.NONE

        # Not enough slack to wait: commit to ON_DEMAND
        self._committed_od = True
        return ClusterType.ON_DEMAND