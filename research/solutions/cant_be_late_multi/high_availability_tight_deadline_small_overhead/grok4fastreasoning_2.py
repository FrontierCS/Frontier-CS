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
        self.no_spot_start = None
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left - self.remaining_restart_overhead < remaining_work:
            return ClusterType.ON_DEMAND

        if has_spot:
            self.no_spot_start = None
            return ClusterType.SPOT
        else:
            if self.no_spot_start is None:
                self.no_spot_start = self.env.elapsed_seconds
            no_spot_duration = self.env.elapsed_seconds - self.no_spot_start
            if no_spot_duration > 3600.0:
                current_region = self.env.get_current_region()
                num_regions = self.env.get_num_regions()
                if num_regions > 1:
                    next_region = (current_region + 1) % num_regions
                    self.env.switch_region(next_region)
                self.no_spot_start = None
            return ClusterType.ON_DEMAND