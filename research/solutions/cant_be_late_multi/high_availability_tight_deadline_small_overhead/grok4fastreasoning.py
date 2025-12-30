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
        self.no_spot_start = None
        self.next_region_idx = 1
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
        if self.env.elapsed_seconds >= self.deadline:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        gap_seconds = self.env.gap_seconds

        if has_spot:
            self.no_spot_start = None
            return ClusterType.SPOT
        else:
            if self.no_spot_start is None:
                self.no_spot_start = self.env.elapsed_seconds
            no_spot_dur = self.env.elapsed_seconds - self.no_spot_start
            switch_threshold = 3600.0  # 1 hour
            if no_spot_dur > switch_threshold and num_regions > 1:
                # Compute remaining to check if safe to switch
                total_done = sum(self.task_done_time)
                remaining_work = self.task_duration - total_done
                remaining_time = self.deadline - self.env.elapsed_seconds
                margin = 2 * self.restart_overhead + gap_seconds
                if remaining_time > remaining_work + margin:
                    # Safe to switch
                    next_r = (current_region + self.next_region_idx) % num_regions
                    self.env.switch_region(next_r)
                    self.next_region_idx = (self.next_region_idx % (num_regions - 1)) + 1
                    self.no_spot_start = None
                    return ClusterType.ON_DEMAND
                # else, fall through to ON_DEMAND without switching
            return ClusterType.ON_DEMAND