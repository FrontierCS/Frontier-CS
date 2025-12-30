import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbmrs_v1"

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
        self._commit_to_ondemand = False
        self._epsilon = 1.0  # small safety slack in seconds
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Remaining work and time
        remaining_work = max(0.0, self.task_duration - sum(self.task_done_time))
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds

        # Time to finish if we commit to On-Demand now
        if self.env.cluster_type == ClusterType.ON_DEMAND:
            od_overhead_now = max(0.0, self.remaining_restart_overhead)
        else:
            od_overhead_now = self.restart_overhead
        t_od_finish_now = remaining_work + od_overhead_now

        # Commit condition: once committed, stick to On-Demand
        if self._commit_to_ondemand or time_left <= t_od_finish_now + self._epsilon:
            self._commit_to_ondemand = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available, if not committed to On-Demand
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide to wait (NONE) or switch to On-Demand
        # If we wait one step, can we still finish on OD?
        time_left_after_wait = time_left - gap
        t_od_finish_after_wait = remaining_work + self.restart_overhead
        if time_left_after_wait > t_od_finish_after_wait + self._epsilon:
            return ClusterType.NONE

        # Otherwise, commit to On-Demand to ensure deadline
        self._commit_to_ondemand = True
        return ClusterType.ON_DEMAND