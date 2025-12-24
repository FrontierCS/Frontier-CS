import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cb_late_multi_threshold_v2"

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
        self._panic_mode = False
        # Safety buffer in seconds to mitigate rounding/edge effects
        self._safety_buffer_seconds = 60.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Compute remaining work and time left
        elapsed = self.env.elapsed_seconds
        time_left = max(self.deadline - elapsed, 0.0)
        work_done = sum(self.task_done_time)
        remaining_work = max(self.task_duration - work_done, 0.0)

        # If nothing left, do nothing
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Determine if we must switch to on-demand to guarantee finishing
        # Account for a single restart overhead needed to (re)launch the job on OD
        required_time_if_od = remaining_work + self.restart_overhead + self._safety_buffer_seconds
        if time_left <= required_time_if_od:
            self._panic_mode = True

        # If already in panic mode, stick to on-demand to guarantee completion
        if self._panic_mode:
            return ClusterType.ON_DEMAND

        # Normal mode: prefer Spot if available; otherwise, wait (NONE)
        if has_spot:
            return ClusterType.SPOT

        # If Spot unavailable, we can afford to wait as long as time_left > required_time_if_od
        # This uses the slack to wait for cheaper Spot to return.
        # If slack becomes insufficient, panic mode will trigger next step.
        return ClusterType.NONE
