import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_fallback_v1"

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

        self._commit_on_demand = False
        self._pending_down_wait_seconds = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        dt = self.env.gap_seconds
        progress = sum(self.task_done_time)
        remain_work = max(0.0, self.task_duration - progress)
        if remain_work <= 0.0:
            return ClusterType.NONE

        time_remaining = self.deadline - self.env.elapsed_seconds

        # Once on OD, stay on OD to avoid extra overhead and guarantee completion.
        if self._commit_on_demand or last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        overhead_to_switch = self.restart_overhead
        fudge = dt  # buffer for discretization and overhead accounting uncertainties

        # If we're running out of time, commit to On-Demand now.
        need_if_switch_now = remain_work + overhead_to_switch
        if time_remaining <= need_if_switch_now + fudge:
            self._commit_on_demand = True
            self._pending_down_wait_seconds = 0.0
            return ClusterType.ON_DEMAND

        # Prefer Spot if available.
        if has_spot:
            self._pending_down_wait_seconds = 0.0
            return ClusterType.SPOT

        # Spot not available. Decide whether to wait (NONE) or failover to OD.
        # If waiting another step risks missing the safe fallback window, switch to OD now.
        if time_remaining - dt <= remain_work + overhead_to_switch + fudge:
            self._commit_on_demand = True
            self._pending_down_wait_seconds = 0.0
            return ClusterType.ON_DEMAND

        # Otherwise, wait to save cost.
        self._pending_down_wait_seconds += dt
        return ClusterType.NONE