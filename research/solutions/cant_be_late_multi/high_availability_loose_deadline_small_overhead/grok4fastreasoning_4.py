import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.env.elapsed_seconds >= self.deadline:
            return ClusterType.NONE

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        safe_ratio = remaining_work / max(remaining_time, 1.0)

        if safe_ratio > 0.9:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            current = self.env.get_current_region()
            num = self.env.get_num_regions()
            next_r = (current + 1) % num
            self.env.switch_region(next_r)
            return ClusterType.ON_DEMAND