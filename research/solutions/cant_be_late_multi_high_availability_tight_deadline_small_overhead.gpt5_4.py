import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "never_late_v2"

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
        self._committed_to_od = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Remaining work and time calculations
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(self.task_duration - done, 0.0)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        # If already committed to on-demand, keep running OD
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # If we cannot afford to waste a full step (worst-case), commit to On-Demand
        # Worst-case trying spot or idling this step: lose one gap with zero work, then OD with one overhead.
        # So we can afford to try spot/idle only if time_left > remaining_work + overhead + gap
        if time_left <= remaining_work + overhead + gap:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise we can still afford to waste one full step: prefer SPOT if available, else idle
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE
