import json
from argparse import Namespace
from typing import List
import math

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
        self.consecutive_no_spot = 0
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
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        done: float = sum(self.task_done_time)
        remaining_work: float = self.task_duration - done
        time_left: float = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds

        if has_spot:
            self.consecutive_no_spot = 0
            return ClusterType.SPOT

        self.consecutive_no_spot += 1

        # Check if time is tight: estimate steps needed
        est_overhead = self.remaining_restart_overhead + self.restart_overhead * 2  # conservative future overheads
        steps_needed = math.ceil((remaining_work + est_overhead) / gap)
        steps_available = math.floor(time_left / gap)
        tight = steps_needed >= steps_available - 1  # leave 1 buffer step

        if tight:
            return ClusterType.ON_DEMAND

        max_tolerate = 3
        if self.consecutive_no_spot > max_tolerate and num_regions > 1:
            next_reg = (current_region + 1) % num_regions
            self.env.switch_region(next_reg)
            self.consecutive_no_spot = 0
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND