import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "safety_first_v1"

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

        self._commit_to_od = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Remaining work
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(0.0, self.task_duration - done)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds
        # Overhead to switch to on-demand (if not already on OD)
        od_switch_overhead = self.restart_overhead

        # If already committed to OD (or already on OD), stay on OD to avoid extra overheads
        if self._commit_to_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Safety rule: If taking one more non-OD step (SPOT or NONE) could make it impossible
        # to finish on OD (with restart overhead), then switch to OD now.
        # Worst-case next step yields zero progress: time_left - gap must still >= remaining_work + od_switch_overhead
        if (time_left - gap) < (remaining_work + od_switch_overhead):
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # If Spot not available, wait if safe; otherwise switch to OD
        if (time_left - gap) >= (remaining_work + od_switch_overhead):
            return ClusterType.NONE

        self._commit_to_od = True
        return ClusterType.ON_DEMAND
