import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cycling_strategy"  # REQUIRED: unique identifier

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
        self.last_len = len(self.task_done_time)
        self.total_done = sum(self.task_done_time)
        self.consecutive_no_spot = 0
        self.num_regions = self.env.get_num_regions()
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
        # Update total_done efficiently
        current_len = len(self.task_done_time)
        if current_len > self.last_len:
            for i in range(self.last_len, current_len):
                self.total_done += self.task_done_time[i]
            self.last_len = current_len

        remaining_work = self.task_duration - self.total_done
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        # If tight on time, use on-demand reliably, no switching
        if (remaining_time - self.remaining_restart_overhead) < remaining_work * 1.2:
            return ClusterType.ON_DEMAND

        current = self.env.get_current_region()
        if has_spot:
            self.consecutive_no_spot = 0
            return ClusterType.SPOT
        else:
            self.consecutive_no_spot += 1
            if self.consecutive_no_spot >= 3 and self.num_regions > 1:
                next_r = (current + 1) % self.num_regions
                self.env.switch_region(next_r)
                self.consecutive_no_spot = 0
            return ClusterType.ON_DEMAND