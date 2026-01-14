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

        # Load traces
        self.traces: List[List[bool]] = []
        trace_files = config.get("trace_files", [])
        for path in trace_files:
            with open(path, 'r') as tf:
                self.traces.append(json.load(tf))  # Assume list of bools per timestep

        return self

    def _get_streak(self, region: int, step: int) -> int:
        if step >= len(self.traces[region]):
            return 0
        streak = 0
        while step + streak < len(self.traces[region]) and self.traces[region][step + streak]:
            streak += 1
        return streak

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
        current_r = self.env.get_current_region()
        num_r = self.env.get_num_regions()
        gap = self.env.gap_seconds
        current_step = int(self.env.elapsed_seconds // gap)

        # Find best region for spot streak starting now
        max_streak = 0
        best_r = current_r
        for r in range(num_r):
            streak = self._get_streak(r, current_step)
            if streak > max_streak:
                max_streak = streak
                best_r = r

        if max_streak > 0:
            if best_r != current_r:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            # No spot now, find best for next step
            next_step = current_step + 1
            max_streak = 0
            best_r = current_r
            for r in range(num_r):
                streak = self._get_streak(r, next_step) if next_step < len(self.traces[r]) else 0
                if streak > max_streak:
                    max_streak = streak
                    best_r = r
            if best_r != current_r:
                self.env.switch_region(best_r)
            return ClusterType.ON_DEMAND