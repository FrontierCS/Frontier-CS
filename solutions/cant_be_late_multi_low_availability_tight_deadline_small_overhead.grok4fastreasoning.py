import json
from argparse import Namespace
from typing import Any

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
        self.consecutive_skips = 0
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
        total_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_done
        if remaining_work <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        remaining_time = self.deadline - current_time
        slack = remaining_time - remaining_work

        if has_spot:
            self.consecutive_skips = 0
            return ClusterType.SPOT

        self.consecutive_skips += 1
        num_r = self.env.get_num_regions()
        threshold = 7200.0  # 2 hours in seconds
        if self.consecutive_skips >= num_r or slack < threshold:
            self.consecutive_skips = 0
            return ClusterType.ON_DEMAND
        else:
            curr_r = self.env.get_current_region()
            next_r = (curr_r + 1) % num_r
            self.env.switch_region(next_r)
            return ClusterType.NONE
