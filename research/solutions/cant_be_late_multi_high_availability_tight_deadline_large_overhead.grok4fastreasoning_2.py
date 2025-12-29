import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "switching_strategy"

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
        self.no_spot_count = 0
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
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        remaining_time = self.deadline - self.env.elapsed_seconds

        if remaining_work <= 0:
            return ClusterType.NONE

        urgent = remaining_work > remaining_time - self.remaining_restart_overhead

        if has_spot:
            self.no_spot_count = 0
            return ClusterType.SPOT

        self.no_spot_count += 1

        do_switch = False
        if (self.no_spot_count >= 3 and
            not urgent and
            self.env.get_num_regions() > 1 and
            remaining_time > remaining_work + self.restart_overhead + self.remaining_restart_overhead):
            do_switch = True

        if do_switch:
            current = self.env.get_current_region()
            new_region = (current + 1) % self.env.get_num_regions()
            self.env.switch_region(new_region)
            self.no_spot_count = 0

        return ClusterType.ON_DEMAND