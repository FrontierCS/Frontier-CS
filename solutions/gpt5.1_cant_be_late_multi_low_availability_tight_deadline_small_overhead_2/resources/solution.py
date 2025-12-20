import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region, deadline-aware scheduling strategy."""
    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        deadline_h = float(config["deadline"])
        duration_h = float(config["duration"])
        overhead_h = float(config["overhead"])

        args = Namespace(
            deadline_hours=deadline_h,
            task_duration_hours=[duration_h],
            restart_overhead_hours=[overhead_h],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Convert hours to seconds for our own computations.
        slack_h = max(0.0, deadline_h - duration_h)
        slack_s = slack_h * 3600.0
        overhead_s = overhead_h * 3600.0

        # Slack threshold: how much slack we want to keep when switching to OD only.
        # Use ~20% of total slack, at least max(1h, 6 * overhead).
        base_threshold = slack_s * 0.2 if slack_s > 0.0 else 0.0
        self._slack_threshold = max(base_threshold, overhead_s * 6.0, 3600.0)

        # Progress tracking.
        self._progress_seconds = 0.0
        self._last_task_done_idx = 0

        # Mode flags.
        self._use_od_only = False

        # Region state will be initialized lazily.
        self._initialized_custom = False

        return self

    def _initialize_custom_state(self):
        if getattr(self, "_initialized_custom", False):
            return

        # Ensure basic fields exist even if solve() was not used (defensive).
        if not hasattr(self, "_progress_seconds"):
            self._progress_seconds = 0.0
        if not hasattr(self, "_last_task_done_idx"):
            self._last_task_done_idx = 0
        if not hasattr(self, "_use_od_only"):
            self._use_od_only = False
        if not hasattr(self, "_slack_threshold"):
            overhead = float(getattr(self, "restart_overhead", 0.0))
            # Fallback: 2h or 10 * overhead or 1h, whichever is largest.
            self._slack_threshold = max(2 * 3600.0, 10.0 * overhead, 3600.0)

        try:
            num_regions = self.env.get_num_regions()
        except Exception:
            num_regions = 1

        self._num_regions = num_regions
        self._region_obs = [0] * num_regions
        self._region_spot = [0] * num_regions
        self._min_region_obs = 10  # Number of observations per region before exploitation.

        self._initialized_custom = True

    def _update_progress(self):
        # Incrementally track cumulative useful work.
        n = len(self.task_done_time)
        last_n = self._last_task_done_idx
        if n > last_n:
            new_sum = 0.0
            data = self.task_done_time
            for i in range(last_n, n):
                new_sum += data[i]
            self._progress_seconds += new_sum
            self._last_task_done_idx = n

    def _select_best_region(self, current_region: int) -> int:
        # Choose region for future spot attempts when current region lacks spot.
        num_regions = self._num_regions
        if num_regions <= 1:
            return current_region

        best_region = current_region
        best_score = float("-inf")
        min_obs = self._min_region_obs

        for r in range(num_regions):
            obs = self._region_obs[r]
            if obs < min_obs:
                # Strongly prioritize under-explored regions.
                score = 1_000_000.0 - obs
            else:
                # Exploit: use empirical availability.
                score = self._region_spot[r] / obs if obs > 0 else 0.0
            if score > best_score:
                best_score = score
                best_region = r

        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_custom_state()
        self._update_progress()

        task_duration = self.task_duration
        deadline = self.deadline

        progress = self._progress_seconds
        if progress >= task_duration:
            # Task completed; no need to run more.
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = deadline - elapsed
        if time_left <= 0.0:
            # Already past deadline; still use OD as best-effort.
            self._use_od_only = True
            return ClusterType.ON_DEMAND

        work_left = task_duration - progress
        if work_left < 0.0:
            work_left = 0.0

        slack = time_left - work_left

        # Update region statistics for current observation.
        current_region = self.env.get_current_region() if self._num_regions > 0 else 0
        if self._num_regions > 0:
            self._region_obs[current_region] += 1
            if has_spot:
                self._region_spot[current_region] += 1

        # Decide if we should switch permanently to on-demand.
        if not self._use_od_only:
            if slack <= self._slack_threshold:
                self._use_od_only = True

        if self._use_od_only:
            # In OD-only mode: always run OD, never change regions to avoid extra overhead.
            return ClusterType.ON_DEMAND

        # Spot-preferred mode.
        if has_spot:
            # Use spot whenever available in the current region.
            return ClusterType.SPOT

        # No spot here: choose a (possibly) better region for future and wait (NONE).
        best_region = self._select_best_region(current_region)
        if best_region != current_region:
            self.env.switch_region(best_region)
        return ClusterType.NONE
