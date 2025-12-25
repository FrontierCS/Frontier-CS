import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "lazy_fallback_od"

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

        # Internal state
        self._work_done_cache = 0.0
        self._done_index = 0
        self.lock_on_od = False
        return self

    def _update_work_done_cache(self):
        td_list = self.task_done_time
        idx = len(td_list)
        if idx > self._done_index:
            self._work_done_cache += sum(td_list[self._done_index:idx])
            self._done_index = idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress efficiently
        self._update_work_done_cache()

        # Derived quantities
        work_remaining = max(self.task_duration - self._work_done_cache, 0.0)
        if work_remaining <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            self.lock_on_od = True
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # Once we commit to On-Demand, never leave it to avoid extra overhead.
        if self.lock_on_od or last_cluster_type == ClusterType.ON_DEMAND:
            self.lock_on_od = True
            return ClusterType.ON_DEMAND

        # If we cannot afford idling one more step and then switching to OD, commit to OD now.
        # Safe idling condition: time_left - gap >= work_remaining + overhead
        if time_left - gap < work_remaining + overhead - 1e-9:
            self.lock_on_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, we have slack for at least one more step.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and safe to idle.
        return ClusterType.NONE
