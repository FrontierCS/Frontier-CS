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
        self.consecutive_no_spot = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        curr_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        if has_spot:
            self.consecutive_no_spot = 0
            return ClusterType.SPOT
        else:
            self.consecutive_no_spot += 1
            if self.consecutive_no_spot >= 2 and num_regions > 1:
                new_region = (curr_region + 1) % num_regions
                self.env.switch_region(new_region)
                self.consecutive_no_spot = 0
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
