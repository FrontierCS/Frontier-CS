import json
from argparse import Namespace
import math

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
        self.region_history = {}
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE

        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        time_ratio = remaining_time / self.task_duration if self.task_duration > 0 else 0

        spot_ratio = 0.9701 / 3.06
        conservative = time_ratio < 1.2

        # Update region history
        if current_region not in self.region_history:
            self.region_history[current_region] = {"spot_seen": 0, "total_steps": 0}
        self.region_history[current_region]["total_steps"] += 1
        if has_spot:
            self.region_history[current_region]["spot_seen"] += 1

        if remaining_work <= 0:
            return ClusterType.NONE

        if remaining_time <= remaining_work + self.restart_overhead:
            return ClusterType.ON_DEMAND

        # Conservative mode: use on-demand if we're running out of time
        if conservative:
            if remaining_time < remaining_work * 1.5:
                return ClusterType.ON_DEMAND

        # Try to use spot if available
        if has_spot:
            # Check if we should switch to a region with better spot history
            best_region = current_region
            best_score = -1
            for region in range(num_regions):
                if region in self.region_history:
                    hist = self.region_history[region]
                    if hist["total_steps"] > 0:
                        score = hist["spot_seen"] / hist["total_steps"]
                        if score > best_score:
                            best_score = score
                            best_region = region
                elif best_score < 0:
                    best_region = region
                    best_score = 0
            
            if best_region != current_region and remaining_time > remaining_work * 2:
                self.env.switch_region(best_region)
                return ClusterType.NONE
            
            return ClusterType.SPOT

        # No spot available in current region
        # Try to find a region with spot (if we have enough time)
        if remaining_time > remaining_work * 1.5:
            for region in range(num_regions):
                if region == current_region:
                    continue
                # Try switching to this region
                self.env.switch_region(region)
                return ClusterType.NONE
        
        # Default to on-demand if no spot and not enough time to switch
        return ClusterType.ON_DEMAND
