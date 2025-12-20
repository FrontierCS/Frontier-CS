import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_heuristic"

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
        self._od_lock = False  # once True, stay on-demand till completion
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we already decided to lock to on-demand, keep using on-demand.
        if self._od_lock:
            return ClusterType.ON_DEMAND

        # Compute remaining work and wall-clock time left
        remaining_work = max(0.0, self.task_duration - sum(self.task_done_time))
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        wall_time_left = self.deadline - elapsed

        # Safety buffer to avoid cutting it too close due to step granularity/overhead application.
        # Choose one gap as buffer.
        safety_buffer = self.env.gap_seconds

        # Time needed to finish on on-demand if we start now.
        # If already on on-demand, only pending overhead (if any) remains; otherwise, we need to pay a fresh restart overhead.
        if self.env.cluster_type == ClusterType.ON_DEMAND:
            od_time_needed = remaining_work + max(0.0, self.remaining_restart_overhead)
        else:
            od_time_needed = remaining_work + self.restart_overhead

        # If we do not have enough time to safely wait or use spot, lock to on-demand immediately.
        if wall_time_left <= od_time_needed + safety_buffer:
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available here: we can either wait (NONE) or use on-demand.
        # Compute the latest time we can wait before we must switch to on-demand:
        # we can wait until deadline - (restart_overhead + remaining_work) - safety_buffer
        latest_wait_time = self.deadline - (self.restart_overhead + remaining_work) - safety_buffer

        if elapsed >= latest_wait_time:
            # Must switch now to guarantee finish.
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # Still have slack to wait for spot to return.
        return ClusterType.NONE
