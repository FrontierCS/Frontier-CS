import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_guard_v2"

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

        # Runtime state (lazy init in _step in case env not ready here)
        self._rt_initialized = False
        self._progress_sum = 0.0
        self._last_len = 0
        self._committed_od = False
        self._num_regions = None
        self._gap = None

        return self

    def _lazy_init_runtime(self):
        if self._rt_initialized:
            return
        self._rt_initialized = True
        # Initialize running sum of progress
        self._last_len = len(self.task_done_time) if hasattr(self, "task_done_time") else 0
        self._progress_sum = 0.0
        if self._last_len > 0:
            # One-time cost at first step only
            self._progress_sum = float(sum(self.task_done_time))
        # Cache environment parameters
        self._num_regions = int(self.env.get_num_regions()) if hasattr(self.env, "get_num_regions") else 1
        self._gap = float(getattr(self.env, "gap_seconds", 0.0))

    def _update_progress_sum(self):
        # Incrementally update progress sum with only new segments
        current_len = len(self.task_done_time)
        if current_len > self._last_len:
            # Sum only new entries
            added = 0.0
            for i in range(self._last_len, current_len):
                added += self.task_done_time[i]
            self._progress_sum += added
            self._last_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init_runtime()
        self._update_progress_sum()

        # Remaining work and time
        remaining_work = max(0.0, float(self.task_duration) - self._progress_sum)
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)

        # If already finished, do nothing
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If already committed to On-Demand, stay on it until completion
        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Compute overhead to start OD now
        overhead_to_od = 0.0 if self.env.cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)

        # Latest-safe-start check: if we must start OD now to guarantee finish
        if time_left <= remaining_work + overhead_to_od:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide whether to wait (NONE) or switch to OD
        # We can afford to wait one full gap if after waiting we could still finish using OD
        if self._gap > 0.0 and (time_left - self._gap) > (remaining_work + overhead_to_od):
            # Opportunistically rotate region to seek availability next step
            if self._num_regions and self._num_regions > 1:
                next_region = (self.env.get_current_region() + 1) % self._num_regions
                self.env.switch_region(next_region)
            return ClusterType.NONE

        # Not enough slack to wait; commit to OD
        self._committed_od = True
        return ClusterType.ON_DEMAND