import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbmrs_jit_v1"

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
        self._accum_done = 0.0
        self._last_len = 0
        self._od_locked = False
        self._margin_sec = None  # initialized on first step
        return self

    def _update_done(self):
        new_len = len(self.task_done_time)
        if new_len > self._last_len:
            # Incrementally accumulate new segments
            for i in range(self._last_len, new_len):
                self._accum_done += self.task_done_time[i]
            self._last_len = new_len

    def _should_lock_od(self, time_left: float, work_left: float) -> bool:
        # Latest time to start OD and still finish: time_left <= work_left + overhead + margin
        margin = self._margin_sec if self._margin_sec is not None else 0.0
        return time_left <= (work_left + self.restart_overhead + margin)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize margin adaptively at first call
        if self._margin_sec is None:
            # Safety buffer to avoid missing deadline due to discretization/overheads
            # Use 20% of step or at least 60s; capped not to exceed restart_overhead excessively
            base_margin = max(60.0, 0.2 * float(self.env.gap_seconds))
            # Don't exceed restart_overhead too much to avoid unnecessary early OD
            self._margin_sec = min(base_margin, self.restart_overhead)

        # Update accumulated done work efficiently
        self._update_done()

        work_left = max(0.0, self.task_duration - self._accum_done)
        if work_left <= 0.0:
            return ClusterType.NONE

        # If we've already locked to OD fallback, stay on OD to avoid extra overhead/risk
        if self._od_locked or last_cluster_type == ClusterType.ON_DEMAND:
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Compute remaining wall-clock time
        time_left = self.deadline - self.env.elapsed_seconds

        # If it's time to lock OD to guarantee finishing, do it
        if self._should_lock_od(time_left, work_left):
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Opportunistically use SPOT when available
        if has_spot:
            return ClusterType.SPOT

        # Otherwise wait (NONE) to save cost; rely on OD fallback when necessary
        return ClusterType.NONE