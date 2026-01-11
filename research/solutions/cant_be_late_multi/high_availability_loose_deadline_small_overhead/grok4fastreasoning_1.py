import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "switching_strategy"

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
        self.no_spot_streak = 0
        self.num_regions = self.env.get_num_regions()
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        if has_spot:
            self.no_spot_streak = 0
            return ClusterType.SPOT
        else:
            self.no_spot_streak += 1
            if self.no_spot_streak >= 3:
                new_region = (current_region + 1) % self.num_regions
                self.env.switch_region(new_region)
                self.no_spot_streak = 0
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND