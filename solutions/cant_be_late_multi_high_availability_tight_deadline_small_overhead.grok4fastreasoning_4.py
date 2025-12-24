import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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
        self.streak_no_spot = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE

        remaining_work = self.task_duration - progress
        time_left = self.deadline - self.env.elapsed_seconds
        effective_time_left = time_left - self.remaining_restart_overhead
        if remaining_work > effective_time_left:
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        if has_spot:
            self.streak_no_spot = 0
            return ClusterType.SPOT
        else:
            self.streak_no_spot += 1
            no_spot_duration = self.streak_no_spot * gap
            if no_spot_duration > 2 * self.restart_overhead:
                current = self.env.get_current_region()
                num = self.env.get_num_regions()
                if num > 1:
                    new_region = (current + 1) % num
                    self.env.switch_region(new_region)
                    self.streak_no_spot = 0
            return ClusterType.ON_DEMAND
