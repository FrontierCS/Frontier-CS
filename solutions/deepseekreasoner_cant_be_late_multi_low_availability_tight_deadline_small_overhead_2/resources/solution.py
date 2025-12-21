import json
import math
from argparse import Namespace
from enum import IntEnum

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_threshold"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.spot_price / self.ondemand_price
        self.consecutive_no_spot = 0
        self.last_region = None
        self.region_streak = 0
        self.switch_threshold = 3
        self.wait_threshold = 2
        self.panic_mode = False

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
        if self.last_region != current_region:
            self.last_region = current_region
            self.region_streak = 1
        else:
            self.region_streak += 1

        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE

        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        work_steps_needed = math.ceil(remaining_work / self.env.gap_seconds)
        overhead_steps = math.ceil(self.restart_overhead / self.env.gap_seconds)

        if last_cluster_type != ClusterType.ON_DEMAND:
            min_steps_on_demand = overhead_steps + work_steps_needed
        else:
            min_steps_on_demand = work_steps_needed

        min_time_on_demand = min_steps_on_demand * self.env.gap_seconds

        if min_time_on_demand > time_left:
            self.panic_mode = True

        if self.panic_mode:
            return ClusterType.ON_DEMAND

        if has_spot:
            self.consecutive_no_spot = 0
            return ClusterType.SPOT
        else:
            self.consecutive_no_spot += 1
            if self.consecutive_no_spot >= self.switch_threshold:
                num_regions = self.env.get_num_regions()
                next_region = (current_region + 1) % num_regions
                if next_region != current_region:
                    self.env.switch_region(next_region)
                    self.consecutive_no_spot = 0
                    return ClusterType.NONE
            if self.consecutive_no_spot <= self.wait_threshold:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
