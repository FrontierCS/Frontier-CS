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
        self.no_spot_streak = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        remaining_time = self.deadline - current_time
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work

        # Safety check: if not enough time even without future overheads, force on-demand
        if remaining_work > remaining_time - self.remaining_restart_overhead:
            return ClusterType.ON_DEMAND

        if has_spot:
            self.no_spot_streak = 0
            return ClusterType.SPOT
        else:
            self.no_spot_streak += 1
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            if self.no_spot_streak > 1 and num_regions > 1:
                new_region = (current_region + 1) % num_regions
                self.env.switch_region(new_region)
                self.no_spot_streak = 0
            return ClusterType.ON_DEMAND