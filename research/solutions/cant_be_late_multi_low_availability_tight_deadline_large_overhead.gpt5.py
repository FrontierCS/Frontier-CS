import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_guard_simple"

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
        self._commit_od = False  # Once True, always run On-Demand until finish
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to On-Demand, continue to run OD.
        if self._commit_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_od = True
            return ClusterType.ON_DEMAND

        # Compute remaining work and time left
        gap = float(self.env.gap_seconds)
        remaining = max(0.0, float(self.task_duration) - float(sum(self.task_done_time)))
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        overhead = float(self.restart_overhead)

        # If somehow finished, do nothing
        if remaining <= 1e-9:
            return ClusterType.NONE

        # Determine the latest safe time to switch to On-Demand.
        # Upper bound time to finish on OD if starting now:
        #   T_up = overhead + remaining + gap (rounding upper bound)
        # We must commit before time_left drops below this window.
        T_up = overhead + remaining + gap

        # If we cannot afford to wait further, commit to On-Demand now.
        if time_left <= T_up + 1e-9:
            self._commit_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot when available to save cost; else wait.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE