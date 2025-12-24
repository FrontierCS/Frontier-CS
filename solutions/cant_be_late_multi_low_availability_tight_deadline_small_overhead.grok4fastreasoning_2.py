import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

class Solution(MultiRegionStrategy):
    NAME = "searching_strategy"

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
        self.total_done = sum(self.task_done_time)
        self.prev_len = len(self.task_done_time)
        self.consecutive_pauses = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_len = len(self.task_done_time)
        for i in range(self.prev_len, current_len):
            self.total_done += self.task_done_time[i]
        self.prev_len = current_len

        remaining_work = self.task_duration - self.total_done
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_time <= 0:
            return ClusterType.NONE

        steps_needed = remaining_work / self.env.gap_seconds
        steps_avail = remaining_time / self.env.gap_seconds
        safety_margin = 1.2
        if steps_needed > steps_avail / safety_margin:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        if has_spot:
            self.consecutive_pauses = 0
            return ClusterType.SPOT

        if last_cluster_type == ClusterType.ON_DEMAND:
            self.consecutive_pauses = 0
            return ClusterType.ON_DEMAND

        num_r = self.env.get_num_regions()
        if last_cluster_type == ClusterType.SPOT:
            current = self.env.get_current_region()
            new_r = (current + 1) % num_r
            self.env.switch_region(new_r)
            self.consecutive_pauses = 1
            return ClusterType.NONE
        else:
            self.consecutive_pauses += 1
            if self.consecutive_pauses >= num_r:
                self.consecutive_pauses = 0
                return ClusterType.ON_DEMAND
            else:
                current = self.env.get_current_region()
                new_r = (current + 1) % num_r
                self.env.switch_region(new_r)
                return ClusterType.NONE
