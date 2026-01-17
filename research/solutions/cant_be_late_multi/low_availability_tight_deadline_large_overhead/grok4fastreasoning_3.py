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
        self.no_spot_count = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        if has_spot:
            self.no_spot_count = 0
            return ClusterType.SPOT

        self.no_spot_count += 1
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        if self.no_spot_count >= 2 and num_regions > 1:
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            self.no_spot_count = 0

        time_left = self.deadline - self.env.elapsed_seconds - self.remaining_restart_overhead
        if remaining_work > time_left:
            return ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND