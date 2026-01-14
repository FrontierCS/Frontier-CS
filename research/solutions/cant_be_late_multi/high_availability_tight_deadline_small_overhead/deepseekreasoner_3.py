import json
from argparse import Namespace
from typing import List, Tuple
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
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
        self.region_stats = []  # list of [available_count, total_count] per region
        self.consecutive_no_spot = 0
        self.current_region = 0
        self.last_cluster_type = ClusterType.NONE
        self.gap_seconds = 3600.0  # default, will be updated in first _step

        return self

    def _get_best_region(self) -> int:
        """Return the region index with the highest historical spot availability."""
        best_region = 0
        best_ratio = -1.0
        for idx, (avail, total) in enumerate(self.region_stats):
            ratio = avail / total if total > 0 else 0.0
            if ratio > best_ratio:
                best_ratio = ratio
                best_region = idx
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Update gap_seconds if available
        if hasattr(self.env, 'gap_seconds'):
            self.gap_seconds = self.env.gap_seconds
        else:
            self.gap_seconds = 3600.0

        # Update current region
        self.current_region = self.env.get_current_region()

        # Ensure region_stats list is long enough
        while len(self.region_stats) <= self.current_region:
            self.region_stats.append([0, 0])

        # Update statistics for current region
        if has_spot:
            self.region_stats[self.current_region][0] += 1
            self.consecutive_no_spot = 0
        else:
            self.consecutive_no_spot += 1
        self.region_stats[self.current_region][1] += 1

        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds

        # Calculate time needed if we switch to on-demand now
        gap = self.gap_seconds
        overhead = self.restart_overhead
        if self.last_cluster_type == ClusterType.ON_DEMAND and self.remaining_restart_overhead <= 0:
            # Already on on-demand with no pending overhead
            steps_needed = math.ceil(remaining_work / gap)
            time_needed_ondemand = steps_needed * gap
        else:
            # Will incur overhead on first step
            work_first_step = max(0, gap - overhead)
            if remaining_work <= work_first_step:
                steps_needed = 1
            else:
                steps_needed = 1 + math.ceil((remaining_work - work_first_step) / gap)
            time_needed_ondemand = steps_needed * gap

        # Safety condition: must use on-demand if time is tight
        if remaining_time <= time_needed_ondemand:
            return ClusterType.ON_DEMAND

        # If spot is available, use it
        if has_spot:
            return ClusterType.SPOT

        # Spot not available
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Continue on-demand
            return ClusterType.ON_DEMAND

        # We were on spot or NONE, and spot is not available now
        if remaining_time <= time_needed_ondemand * 1.2:  # some safety margin
            return ClusterType.ON_DEMAND

        # We can afford to wait for spot
        if last_cluster_type == ClusterType.NONE:
            # We are idle, consider switching region if waited too long
            if self.consecutive_no_spot > 3:
                best_region = self._get_best_region()
                if best_region != self.current_region:
                    self.env.switch_region(best_region)
                    # Reset consecutive counter for the new region
                    self.consecutive_no_spot = 0
            return ClusterType.NONE
        else:
            # We were running spot, stop it and become idle
            return ClusterType.NONE