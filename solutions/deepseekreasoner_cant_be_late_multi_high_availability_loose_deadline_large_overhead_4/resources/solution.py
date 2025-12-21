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
        # custom initialization
        self.no_spot_streak = 0
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
        """
        # If task is already finished, do nothing
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        # Get current state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        remaining_time = self.deadline - self.env.elapsed_seconds

        # Update spot availability streak
        if last_cluster_type == ClusterType.SPOT:
            if has_spot:
                self.no_spot_streak = 0
            else:
                self.no_spot_streak += 1
        elif last_cluster_type == ClusterType.ON_DEMAND and has_spot:
            # reset streak when spot becomes available while on-demand
            self.no_spot_streak = 0

        # If there is pending restart overhead, try to avoid changing cluster type
        if self.remaining_restart_overhead > 0:
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            # otherwise we are forced to change, continue with normal logic

        # Case: not running
        if last_cluster_type == ClusterType.NONE:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # Case: running on spot
        if last_cluster_type == ClusterType.SPOT:
            if has_spot:
                return ClusterType.SPOT
            else:
                # spot became unavailable
                if self.no_spot_streak >= 2 and num_regions > 1:
                    # try another region
                    next_region = (current_region + 1) % num_regions
                    self.env.switch_region(next_region)
                    self.no_spot_streak = 0
                return ClusterType.ON_DEMAND

        # Case: running on on-demand
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Consider switching to spot if available and we have enough slack
            remaining_work = self.task_duration - sum(self.task_done_time)
            if has_spot and remaining_time > remaining_work * 1.5:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # fallback (should not happen)
        return ClusterType.ON_DEMAND
