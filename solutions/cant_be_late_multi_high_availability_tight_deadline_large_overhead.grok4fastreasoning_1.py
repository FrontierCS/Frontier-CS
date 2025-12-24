import json
from argparse import Namespace

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
        self.total_done = 0.0
        self.last_len = 0
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
            added_sum = sum(self.task_done_time[self.last_len:])
            self.total_done += added_sum
            self.last_len = current_len

        remaining_work = self.task_duration - self.total_done
        remaining_time = self.deadline - self.env.elapsed_seconds
        time_needed = remaining_work + self.remaining_restart_overhead

        must_run = time_needed > remaining_time

        if has_spot:
            return ClusterType.SPOT
        elif must_run:
            return ClusterType.ON_DEMAND
        else:
            # Pause and switch to next region to search for spot availability
            current = self.env.get_current_region()
            num = self.env.get_num_regions()
            next_r = (current + 1) % num
            self.env.switch_region(next_r)
            return ClusterType.NONE
