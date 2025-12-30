import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "slack_guard_v1"

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
        self._committed = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Compute remaining work and time left
        remaining_work = max(0.0, self.task_duration - sum(self.task_done_time))
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            self._committed = True
            return ClusterType.ON_DEMAND

        dt = self.env.gap_seconds
        # Slack buffer after accounting for one restart to commit to ON_DEMAND
        slack = time_left - (self.restart_overhead + remaining_work)

        if self._committed:
            return ClusterType.ON_DEMAND

        # If we are already on ON_DEMAND, stay committed to avoid extra restarts
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed = True
            return ClusterType.ON_DEMAND

        # Commit to ON_DEMAND if we are running out of slack
        safety_margin = dt
        if slack <= safety_margin:
            self._committed = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT if available while we have enough slack
        if has_spot:
            return ClusterType.SPOT

        # If SPOT is not available, idle if we have sufficient slack; else commit to ON_DEMAND
        if slack > 2.0 * dt:
            return ClusterType.NONE
        else:
            self._committed = True
            return ClusterType.ON_DEMAND