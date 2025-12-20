import json
import random
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state for scheduling
        self._region_init = False
        self._alpha = []
        self._beta = []
        self._done_sum = 0.0
        self._done_len = 0
        self._od_committed = False
        self._buffer_seconds = None
        self._switch_cooldown_steps = 1
        self._last_switch_step = -10**9
        self._step_counter = 0
        self._last_region_for_obs = None

        return self

    def _ensure_initialized(self):
        if not self._region_init:
            n = self.env.get_num_regions()
            self._alpha = [1.0] * n
            self._beta = [1.0] * n
            self._region_init = True
        if self._buffer_seconds is None:
            # Conservative buffer to protect against discretization and restart overheads
            # Use the max of: 10 minutes, 2 * restart_overhead, 2 * gap_seconds
            self._buffer_seconds = max(10 * 60.0, 2.0 * self.restart_overhead, 2.0 * self.env.gap_seconds)

    def _update_progress_cache(self):
        if self._done_len != len(self.task_done_time):
            # Incremental sum to avoid O(n^2)
            added = 0.0
            for v in self.task_done_time[self._done_len:]:
                added += v
            self._done_sum += added
            self._done_len = len(self.task_done_time)

    def _choose_best_region(self, prefer_current=True):
        # Thompson sampling over regions
        n = len(self._alpha)
        samples = []
        for i in range(n):
            a = self._alpha[i]
            b = self._beta[i]
            # Avoid degenerate parameters
            if a <= 0.0:
                a = 1e-3
            if b <= 0.0:
                b = 1e-3
            s = random.betavariate(a, b)
            samples.append(s)
        best_idx = max(range(n), key=lambda i: samples[i])

        if prefer_current:
            # Mild stickiness to reduce thrashing: if current is close to best, stick.
            cur = self.env.get_current_region()
            if samples[best_idx] - samples[cur] < 0.03:
                return cur
        return best_idx

    def _od_time_needed(self, last_cluster_type):
        # Time needed to finish on OD from now, including overhead to switch if not already on OD
        remaining_work = max(0.0, self.task_duration - self._done_sum)
        overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return remaining_work + overhead

    def _should_commit_to_od(self, last_cluster_type):
        time_remaining = self.deadline - self.env.elapsed_seconds
        return time_remaining <= self._od_time_needed(last_cluster_type) + self._buffer_seconds

    def _safe_to_wait_one_step(self, last_cluster_type):
        # Check if we can wait one step (NONE) and still be safe to complete on OD afterward
        time_remaining = self.deadline - self.env.elapsed_seconds
        future_time_remaining = time_remaining - self.env.gap_seconds
        return future_time_remaining > self._od_time_needed(last_cluster_type) + self._buffer_seconds

    def _update_region_stats(self, obs_region, has_spot):
        # Update Beta posterior with observed availability in the current region for this step
        if obs_region is not None:
            if has_spot:
                self._alpha[obs_region] += 1.0
            else:
                self._beta[obs_region] += 1.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()
        self._update_progress_cache()

        # If task is already done, do nothing
        if self._done_sum >= self.task_duration:
            return ClusterType.NONE

        self._step_counter += 1

        # Observe has_spot for current region before any potential switch
        current_region = self.env.get_current_region()
        self._update_region_stats(current_region, has_spot)

        # Decide if we must commit to on-demand to guarantee finish
        if not self._od_committed and self._should_commit_to_od(last_cluster_type):
            self._od_committed = True

        if self._od_committed:
            # Once committed, stay on OD to avoid repeated overhead
            return ClusterType.ON_DEMAND

        # Opportunistic use of SPOT if available
        if has_spot:
            # If SPOT available, use it in the current region
            return ClusterType.SPOT

        # SPOT not available in current region: decide to wait or switch to OD
        # If safe to wait one more step, wait; optionally switch region to one with higher estimated availability
        if self._safe_to_wait_one_step(last_cluster_type):
            # Choose a region with better spot availability estimate for future steps
            best_region = self._choose_best_region(prefer_current=True)
            if best_region != current_region and (self._step_counter - self._last_switch_step) >= self._switch_cooldown_steps:
                self.env.switch_region(best_region)
                self._last_switch_step = self._step_counter
            return ClusterType.NONE

        # Not safe to wait anymore: switch to OD
        return ClusterType.ON_DEMAND
