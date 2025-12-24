import json
from argparse import Namespace
import sys

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_deadline_aware_switcher"

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

        self.initialized = False
        return self

    def _initialize(self):
        if self.initialized:
            return
        
        num_regions = self.env.get_num_regions()
        
        self.last_spot_failure_time = [-1.0] * num_regions
        self.SAFETY_MARGIN_FACTOR = 1.5

        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize()

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed_seconds = self.env.elapsed_seconds
        time_to_deadline = self.deadline - elapsed_seconds

        min_time_to_finish_reliably = remaining_work + self.remaining_restart_overhead
        current_slack = time_to_deadline - min_time_to_finish_reliably

        safety_margin = self.SAFETY_MARGIN_FACTOR * self.restart_overhead
        is_panicking = current_slack <= safety_margin

        if is_panicking:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        if has_spot:
            self.last_spot_failure_time[current_region] = -1.0
            return ClusterType.SPOT
        else:
            self.last_spot_failure_time[current_region] = elapsed_seconds

            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                best_next_region = -1
                min_failure_time = float('inf')

                for r in range(num_regions):
                    if r == current_region:
                        continue
                    if self.last_spot_failure_time[r] < min_failure_time:
                        min_failure_time = self.last_spot_failure_time[r]
                        best_next_region = r
                
                if best_next_region != -1:
                    self.env.switch_region(best_next_region)
            
            return ClusterType.ON_DEMAND
