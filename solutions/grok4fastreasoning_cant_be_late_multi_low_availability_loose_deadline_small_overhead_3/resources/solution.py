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

        # Load availability traces
        self.availability: List[List[bool]] = []
        trace_files = config.get("trace_files", [])
        self.num_regions = len(trace_files)
        for path in trace_files:
            with open(path, 'r') as f:
                avail = json.load(f)
                self.availability.append(avail)

        # Precompute future streaks
        self.future_streak: List[List[int]] = []
        num_steps = len(self.availability[0]) if self.availability else 0
        for r in range(self.num_regions):
            streak = [0] * num_steps
            if num_steps > 0 and self.availability[r][num_steps - 1]:
                streak[num_steps - 1] = 1
            for t in range(num_steps - 2, -1, -1):
                if self.availability[r][t]:
                    streak[t] = 1 + streak[t + 1]
            self.future_streak.append(streak)

        # Get gap_seconds
        try:
            self.gap_seconds = self.env.gap_seconds
        except AttributeError:
            self.gap_seconds = 3600.0

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
        current_step = int(self.env.elapsed_seconds // self.gap_seconds)
        num_steps = len(self.availability[0]) if self.availability else 0
        if current_step >= num_steps:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        # Find best region with spot available now and max future streak
        best_region = -1
        max_streak = -1
        for r in range(self.num_regions):
            if current_step < len(self.availability[r]) and self.availability[r][current_step]:
                streak = self.future_streak[r][current_step]
                if streak > max_streak:
                    max_streak = streak
                    best_region = r

        if max_streak > 0:
            if best_region != current_region:
                self.env.switch_region(best_region)
            return ClusterType.SPOT
        else:
            # No spot available anywhere, use ON_DEMAND in current region
            return ClusterType.ON_DEMAND
