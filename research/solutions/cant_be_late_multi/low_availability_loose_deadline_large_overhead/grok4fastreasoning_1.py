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
        self.consecutive_pauses = 0
        self.in_ondemand_mode = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done_work = sum(self.task_done_time)
        if done_work >= self.task_duration:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        gap = self.env.gap_seconds
        work_left = self.task_duration - done_work
        time_left = self.deadline - self.env.elapsed_seconds

        if has_spot:
            self.consecutive_pauses = 0
            self.in_ondemand_mode = False
            return ClusterType.SPOT
        else:
            if self.in_ondemand_mode:
                return ClusterType.ON_DEMAND
            else:
                # Check if we should resort to on-demand due to time constraints
                search_time_estimate = num_regions * gap
                if time_left < work_left + search_time_estimate:
                    self.in_ondemand_mode = True
                    self.consecutive_pauses = 0
                    return ClusterType.ON_DEMAND

                if self.consecutive_pauses >= num_regions - 1:
                    self.in_ondemand_mode = True
                    self.consecutive_pauses = 0
                    return ClusterType.ON_DEMAND
                else:
                    next_region = (current_region + 1) % num_regions
                    self.env.switch_region(next_region)
                    self.consecutive_pauses += 1
                    return ClusterType.NONE