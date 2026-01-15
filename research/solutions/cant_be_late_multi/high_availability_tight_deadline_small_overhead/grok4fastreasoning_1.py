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

        # Load traces assuming each is a JSON list of booleans for availability per timestep
        self.traces: List[List[bool]] = []
        for path in config["trace_files"]:
            with open(path, 'r') as tf:
                trace = json.load(tf)
                self.traces.append(trace)

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
        if done_work >= self.task_duration:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        step_idx = int(elapsed // gap)

        # Find regions with spot available at next step
        spot_regions = [
            r for r in range(num_regions)
            if step_idx < len(self.traces[r]) and self.traces[r][step_idx]
        ]

        if spot_regions:
            # Choose region with longest consecutive spot availability streak starting from step_idx
            best_r = -1
            max_streak = -1
            for r in spot_regions:
                streak = 0
                t = step_idx
                while t < len(self.traces[r]) and self.traces[r][t]:
                    streak += 1
                    t += 1
                if streak > max_streak:
                    max_streak = streak
                    best_r = r
            target = best_r

            # Prefer current if it has a good streak, but since we selected best, use it
            if current_region in spot_regions:
                # Check if current has longer or equal streak
                current_streak = 0
                t = step_idx
                while t < len(self.traces[current_region]) and self.traces[current_region][t]:
                    current_streak += 1
                    t += 1
                if current_streak >= max_streak:
                    target = current_region

            if target != current_region:
                self.env.switch_region(target)

            return ClusterType.SPOT
        else:
            # No spot available anywhere, use on-demand in current region
            return ClusterType.ON_DEMAND