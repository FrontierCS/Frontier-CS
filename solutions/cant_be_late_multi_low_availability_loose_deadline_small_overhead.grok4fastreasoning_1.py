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
        self.num_regions = self.env.get_num_regions()
        self.streak = 0
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
        # Your decision logic here
        current = self.env.get_current_region()
        if has_spot:
            self.streak = 0
            return ClusterType.SPOT

        # No spot, check if time is tight
        done_work: float = sum(self.task_done_time)
        work_left = self.task_duration - done_work
        time_left = self.deadline - self.env.elapsed_seconds
        overhead_pending = self.remaining_restart_overhead
        gap = self.env.gap_seconds
        if work_left + overhead_pending > time_left:
            # Tight on time, run on-demand without switching
            self.streak += 1
            return ClusterType.ON_DEMAND

        # Not tight, manage streak and switching
        self.streak += 1
        if self.streak >= 2:
            next_region = (current + 1) % self.num_regions
            self.env.switch_region(next_region)
            self.streak = 0
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.ON_DEMAND
