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
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        elapsed = self.env.elapsed_seconds
        remaining_wall = self.deadline - elapsed
        if remaining_wall <= 0 or remaining_work <= 0:
            return ClusterType.NONE

        # Find regions with spot available
        spot_regions = [r for r in range(num_regions) if self.env.has_spot(r)]

        if spot_regions:
            # Prefer current if available
            target_region = current_region if current_region in spot_regions else spot_regions[0]
            self.env.switch_region(target_region)
            return ClusterType.SPOT
        else:
            # No spot available anywhere, use ON_DEMAND in current region
            return ClusterType.ON_DEMAND