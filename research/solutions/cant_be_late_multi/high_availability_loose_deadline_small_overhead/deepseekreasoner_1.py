import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType
from collections import defaultdict


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
        self._initialize_state()
        return self

    def _initialize_state(self):
        self.region_stats = None
        self.consecutive_no_spot = 0
        self.current_mode = "RISK"
        self.last_action = ClusterType.NONE

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.region_stats is None:
            self.region_stats = defaultdict(lambda: {"total": 0, "available": 0})

        current_region = self.env.get_current_region()
        self.region_stats[current_region]["total"] += 1
        if has_spot:
            self.region_stats[current_region]["available"] += 1
            self.consecutive_no_spot = 0
        else:
            self.consecutive_no_spot += 1

        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        slack = remaining_time - remaining_work

        if remaining_work <= 0:
            return ClusterType.NONE

        if slack < 6 * 3600:
            self.current_mode = "SAFE"
        elif slack > 12 * 3600:
            self.current_mode = "RISK"

        if self.current_mode == "SAFE":
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        if has_spot:
            self.last_action = ClusterType.SPOT
            return ClusterType.SPOT

        if self.consecutive_no_spot >= 3:
            best_region = current_region
            best_availability = -1.0
            for region in range(self.env.get_num_regions()):
                stats = self.region_stats[region]
                if stats["total"] > 0:
                    availability = stats["available"] / stats["total"]
                else:
                    availability = 0.0
                if availability > best_availability:
                    best_availability = availability
                    best_region = region

            if best_region != current_region:
                self.env.switch_region(best_region)
                self.consecutive_no_spot = 0
                self.last_action = ClusterType.NONE
                return ClusterType.NONE

            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        self.last_action = ClusterType.NONE
        return ClusterType.NONE