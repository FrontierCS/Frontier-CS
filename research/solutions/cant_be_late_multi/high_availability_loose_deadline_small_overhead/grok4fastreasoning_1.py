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
        self.total_progress = 0.0
        self.last_list_len = 0
        self.consecutive_no_spot = 0
        self.threshold = None
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
        current_len = len(self.task_done_time)
        if current_len > self.last_list_len:
            num_new = current_len - self.last_list_len
            added = sum(self.task_done_time[-num_new:])
            self.total_progress += added
            self.last_list_len = current_len

        remaining_work = self.task_duration - self.total_progress
        time_left = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds

        if self.threshold is None:
            wait_time_max = 3600.0
            self.threshold = int(wait_time_max / gap) + 1

        if has_spot:
            self.consecutive_no_spot = 0
            return ClusterType.SPOT
        else:
            self.consecutive_no_spot += 1
            do_switch = self.consecutive_no_spot >= self.threshold
            if do_switch:
                current_region = self.env.get_current_region()
                num_regions = self.env.get_num_regions()
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
                self.consecutive_no_spot = 0

            if remaining_work <= 0:
                return ClusterType.NONE

            need_progress = remaining_work > time_left - gap
            if need_progress:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE