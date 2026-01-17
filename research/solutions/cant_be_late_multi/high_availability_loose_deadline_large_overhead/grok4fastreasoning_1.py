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

        # Load availability traces
        self.availability = []
        for trace_path in config["trace_files"]:
            with open(trace_path, "r") as tf:
                self.availability.append(json.load(tf))
        self.gap_seconds = self.env.gap_seconds
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
        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        step_idx = int(elapsed / self.gap_seconds)

        if has_spot:
            return ClusterType.SPOT

        # Find best region with spot at current step_idx and longest future streak
        best_r = -1
        best_streak = 0
        for r in range(self.num_regions):
            if step_idx < len(self.availability[r]) and self.availability[r][step_idx]:
                streak = 1
                for t in range(step_idx + 1, len(self.availability[r])):
                    if self.availability[r][t]:
                        streak += 1
                    else:
                        break
                if streak > best_streak:
                    best_streak = streak
                    best_r = r

        if best_r != -1:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND