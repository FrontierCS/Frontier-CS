import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    NAME = "multi_region_spot_seeker"

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
        # Initialize strategy state
        self.current_region = 0
        self.untried_regions = list(range(1, self.env.get_num_regions()))
        self.no_spot_count = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If there is pending overhead, we must run a cluster to serve it
        if self.remaining_restart_overhead > 0:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # No pending overhead
        if has_spot:
            self.no_spot_count = 0
            return ClusterType.SPOT

        # No spot available in current region
        self.no_spot_count += 1
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # Calculate how many steps we can wait before we must switch to on-demand
        wait_steps = (time_left - (remaining_work + overhead)) / gap
        if wait_steps < 1e-9:  # time is tight
            return ClusterType.ON_DEMAND

        # If we have waited too long in this region and there are other regions to try
        if self.no_spot_count >= 2 and self.untried_regions:
            # Switch to next untried region
            next_region = self.untried_regions.pop(0)
            self.env.switch_region(next_region)
            self.current_region = next_region
            self.no_spot_count = 0
            # Return NONE to observe the new region without running
            return ClusterType.NONE

        # If we have tried all regions, reset the untried list (excluding current)
        if not self.untried_regions and self.env.get_num_regions() > 1:
            self.untried_regions = [
                i for i in range(self.env.get_num_regions())
                if i != self.current_region
            ]

        # Wait in current region
        return ClusterType.NONE