import json
from argparse import Namespace
from typing import List, Tuple
import heapq

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
        
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.ondemand_price / self.spot_price
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        task_done = sum(self.task_done_time)
        remaining_work = self.task_duration - task_done
        gap = self.env.gap_seconds
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        time_left = deadline - elapsed
        overhead = self.restart_overhead
        
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        if time_left <= remaining_work + overhead:
            return ClusterType.ON_DEMAND
        
        efficiency_needed = remaining_work / time_left
        
        if efficiency_needed > 0.9:
            return ClusterType.ON_DEMAND
        
        spot_value = has_spot
        if last_cluster_type == ClusterType.SPOT and spot_value:
            return ClusterType.SPOT
        
        num_regions = self.env.get_num_regions()
        best_region = current_region
        best_value = -1
        
        for region in range(num_regions):
            if region != current_region:
                self.env.switch_region(region)
                break
        
        if has_spot and last_cluster_type != ClusterType.ON_DEMAND:
            return ClusterType.SPOT
        
        if time_left > remaining_work * self.price_ratio + overhead:
            if has_spot:
                return ClusterType.SPOT
            else:
                for region in range(num_regions):
                    if region != current_region:
                        self.env.switch_region(region)
                        return ClusterType.NONE
        
        return ClusterType.ON_DEMAND