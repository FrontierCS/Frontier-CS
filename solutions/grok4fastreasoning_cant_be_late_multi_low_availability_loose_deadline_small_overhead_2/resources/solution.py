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
        self.trace_paths = config["trace_files"]
        self.num_regions = len(self.trace_paths)
        self.avail: List[List[bool]] = []
        for path in self.trace_paths:
            with open(path, 'r') as f:
                trace = json.load(f)
            # Assume trace is a list of 0/1 or bool
            self.avail.append([bool(x) for x in trace])

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
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE

        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0 or remaining_work <= 0:
            return ClusterType.NONE

        gap = self.env.gap_seconds
        steps_possible = time_left // gap
        needed_steps = (remaining_work + gap - 1) // gap
        if needed_steps > steps_possible:
            return ClusterType.ON_DEMAND

        t = int(self.env.elapsed_seconds // gap)
        current_r = self.env.get_current_region()

        # Ensure trace length
        if t >= len(self.avail[0]):
            return ClusterType.ON_DEMAND

        # Verify passed has_spot
        assert has_spot == self.avail[current_r][t]

        if self.avail[current_r][t]:
            return ClusterType.SPOT

        # Find best region with spot: longest streak
        best_r = -1
        best_streak = -1
        for r in range(self.num_regions):
            if t >= len(self.avail[r]) or not self.avail[r][t]:
                continue
            # Compute streak
            streak = 0
            tt = t
            while tt < len(self.avail[r]) and self.avail[r][tt]:
                streak += 1
                tt += 1
            if streak > best_streak:
                best_streak = streak
                best_r = r

        if best_r != -1:
            self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            # No spot available anywhere
            if remaining_work > 0 and time_left > gap:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
