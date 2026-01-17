import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_rot_v1"

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

        # Internal state for efficiency and decisions
        self._initialized = False
        self._commit_to_od = False
        self._cached_done = 0.0
        self._cached_len = 0
        self._num_regions = None
        return self

    def _init_if_needed(self):
        if not self._initialized:
            try:
                self._num_regions = self.env.get_num_regions()
            except Exception:
                self._num_regions = 1
            self._initialized = True

    def _update_done_cache(self):
        curr_len = len(self.task_done_time)
        if curr_len > self._cached_len:
            # Sum only the newly appended segments
            incremental = 0.0
            # Typically one segment per step, but handle any case
            for i in range(self._cached_len, curr_len):
                incremental += self.task_done_time[i]
            self._cached_done += incremental
            self._cached_len = curr_len

    def _ceil_steps_time(self, seconds_needed: float, gap: float) -> float:
        if seconds_needed <= 0:
            return 0.0
        steps = math.ceil(seconds_needed / gap)
        return steps * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()
        self._update_done_cache()

        gap = self.env.gap_seconds
        now = self.env.elapsed_seconds
        time_left = max(self.deadline - now, 0.0)

        remaining = max(self.task_duration - self._cached_done, 0.0)
        if remaining <= 0.0:
            return ClusterType.NONE

        overhead = self.restart_overhead

        # Time needed to finish if we choose ON_DEMAND now
        od_overhead_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead
        od_time_needed_now = self._ceil_steps_time(od_overhead_now + remaining, gap)

        # If we cannot afford to wait anymore, commit to ON_DEMAND
        if time_left <= od_time_needed_now + 1e-9:
            self._commit_to_od = True

        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Prefer SPOT if available, but be careful if switching from ON_DEMAND
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Safety: allow one SPOT step with zero progress worst-case,
                # then switch to OD next step and still finish before deadline.
                od_time_needed_next = self._ceil_steps_time(overhead + remaining, gap)
                if time_left - gap >= od_time_needed_next - 1e-9:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT

        # SPOT not available in current region
        # Decide to wait (NONE + rotate region) if safe, else use ON_DEMAND
        od_time_needed_next = self._ceil_steps_time(overhead + remaining, gap)
        if time_left - gap >= od_time_needed_next - 1e-9:
            # Safe to wait one step for SPOT; rotate region to explore
            if self._num_regions and self._num_regions > 1:
                next_region = (self.env.get_current_region() + 1) % self._num_regions
                self.env.switch_region(next_region)
            return ClusterType.NONE

        # Not safe to wait; use ON_DEMAND
        return ClusterType.ON_DEMAND