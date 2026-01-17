import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_fallback_spot_v2"

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

        # Initialize strategy state
        self._policy_initialized = False
        self._cached_task_done_len = 0
        self._cached_task_done_sum = 0.0
        self._last_elapsed_seconds = -1.0
        self.fallback_mode = False
        self._panic_slack = 0.0
        self._gap = 0.0
        return self

    def _initialize_policy_if_needed(self, current_time: float):
        # Detect new episode or first call
        if (not getattr(self, "_policy_initialized", False)) or (
            self._last_elapsed_seconds != -1.0 and current_time < self._last_elapsed_seconds
        ):
            self._gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
            # Slack threshold before switching permanently to On-Demand.
            # Use restart_overhead + 2 * gap as a conservative buffer.
            self._panic_slack = self.restart_overhead + 2.0 * self._gap

            self._cached_task_done_len = 0
            self._cached_task_done_sum = 0.0
            self.fallback_mode = False
            self._policy_initialized = True

    def _update_progress_cache(self):
        segments = self.task_done_time
        n = len(segments)
        last_n = self._cached_task_done_len

        if n < last_n:
            # Environment reset; clear cache
            self._cached_task_done_len = 0
            self._cached_task_done_sum = 0.0
            last_n = 0

        if n > last_n:
            self._cached_task_done_sum += sum(segments[last_n:n])
            self._cached_task_done_len = n

        return self._cached_task_done_sum

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        t = self.env.elapsed_seconds
        self._initialize_policy_if_needed(t)

        work_done = self._update_progress_cache()
        remaining_work = self.task_duration - work_done
        if remaining_work < 0.0:
            remaining_work = 0.0

        time_left = self.deadline - t
        slack = time_left - remaining_work

        if not self.fallback_mode and slack <= self._panic_slack:
            self.fallback_mode = True

        self._last_elapsed_seconds = t

        # If task already completed, no need to run more.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        if self.fallback_mode:
            return ClusterType.ON_DEMAND

        # Normal mode: use Spot when available, otherwise idle.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE