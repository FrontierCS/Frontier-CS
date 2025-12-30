import json
from argparse import Namespace

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
        total_done = sum(self.task_done_time)
        if total_done >= self.task_duration:
            return ClusterType.NONE
        if has_spot:
            return ClusterType.SPOT
        remaining_work = self.task_duration - total_done
        remaining_time = self.deadline - self.env.elapsed_seconds
        available_time = remaining_time - self.remaining_restart_overhead
        gap = self.env.gap_seconds
        if available_time > gap and remaining_work <= available_time - gap:
            current = self.env.get_current_region()
            num = self.env.get_num_regions()
            new_r = (current + 1) % num
            if new_r != current:
                self.env.switch_region(new_r)
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND