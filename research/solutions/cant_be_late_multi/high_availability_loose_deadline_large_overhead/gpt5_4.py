import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_safe_spot"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_od = False

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
        self._commit_od = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Compute remaining work and time
        remaining_work = max(self.task_duration - sum(self.task_done_time), 0.0)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            self._commit_od = True
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # If already committed to On-Demand, stay there to avoid extra overhead and risk
        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Bail-out rule:
        # If we wait or run spot for one more step and then must switch,
        # we need at least remaining_work + overhead + gap time left.
        # If not enough, commit to On-Demand now.
        if time_left <= remaining_work + overhead + gap:
            self._commit_od = True
            return ClusterType.ON_DEMAND

        # Safe region: prefer Spot when available; otherwise wait to save cost
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait if safe; we re-evaluate every step
        return ClusterType.NONE