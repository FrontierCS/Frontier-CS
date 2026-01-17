import json
import math
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
        self.num_regions = None
        self.region_stats = {}
        self.current_region = 0
        self.last_spot_availability = True
        self.consecutive_failures = 0
        self.safety_margin = 1.2
        self.spot_preference = True
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.num_regions is None:
            self.num_regions = self.env.get_num_regions()
            for i in range(self.num_regions):
                self.region_stats[i] = {"spot_attempts": 0, "spot_success": 0}

        self.current_region = self.env.get_current_region()
        self.last_spot_availability = has_spot

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds

        if work_remaining <= 0:
            return ClusterType.NONE

        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        if time_remaining <= 0:
            return ClusterType.NONE

        # Calculate conservative time needed
        effective_time_needed = work_remaining + overhead
        if time_remaining < effective_time_needed * self.safety_margin:
            self.spot_preference = False

        # Update region statistics
        if last_cluster_type == ClusterType.SPOT:
            self.region_stats[self.current_region]["spot_attempts"] += 1
            if has_spot:
                self.region_stats[self.current_region]["spot_success"] += 1
                self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1

        # Calculate best region
        best_region = self.current_region
        best_score = -1
        for i in range(self.num_regions):
            stats = self.region_stats[i]
            if stats["spot_attempts"] > 0:
                success_rate = stats["spot_success"] / stats["spot_attempts"]
                score = success_rate
                if i == self.current_region and has_spot:
                    score *= 1.2  # Preference for current region if spot available
                if score > best_score:
                    best_score = score
                    best_region = i

        # Switch region if beneficial
        if (best_region != self.current_region and 
            best_score > 0.3 and 
            self.consecutive_failures >= 2):
            self.env.switch_region(best_region)
            self.current_region = best_region
            has_spot = False  # Unknown after switch, assume no spot initially

        # Decision logic
        if not self.spot_preference:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND

        if has_spot:
            if self.consecutive_failures > 3:
                return ClusterType.NONE
            return ClusterType.SPOT
        else:
            # Check if we can afford to wait
            min_time_on_demand = work_remaining + (overhead if last_cluster_type != ClusterType.ON_DEMAND else 0)
            if time_remaining < min_time_on_demand * 1.1:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE