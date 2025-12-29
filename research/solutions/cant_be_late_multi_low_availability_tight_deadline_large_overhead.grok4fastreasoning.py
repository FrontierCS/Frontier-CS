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
        n_regions = self.env.get_num_regions()
        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        remaining_overhead = self.remaining_restart_overhead
        effective_time_left = time_left - remaining_overhead

        if effective_time_left < remaining_work:
            return ClusterType.ON_DEMAND

        slack_seconds = effective_time_left - remaining_work
        search_time = (n_regions - 1) * gap

        if has_spot:
            return ClusterType.SPOT
        else:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if slack_seconds > search_time + gap:
                next_region = (current_region + 1) % n_regions
                self.env.switch_region(next_region)
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND