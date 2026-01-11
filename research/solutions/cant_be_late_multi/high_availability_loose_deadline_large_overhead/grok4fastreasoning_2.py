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
        for path in config["trace_files"]:
            with open(path, 'r') as f:
                lines = f.readlines()
            av = [line.strip() == '1' for line in lines if line.strip()]
            self.availability.append(av)

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

        gap = self.env.gap_seconds
        current_t = int(self.env.elapsed_seconds / gap)

        if current_t >= len(self.availability[0]):
            return ClusterType.NONE

        remaining_overhead = self.remaining_restart_overhead
        if remaining_overhead > 0:
            # Burn overhead without switching
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        # Verify input has_spot
        current_has = self.availability[current_region][current_t] if current_t < len(self.availability[current_region]) else False
        # Note: has_spot should match current_has, but use input for safety

        if has_spot:
            return ClusterType.SPOT

        # Find best region with spot available now and longest streak
        best_r = -1
        max_streak = 0
        for r in range(num_regions):
            if current_t < len(self.availability[r]) and self.availability[r][current_t]:
                streak = 0
                for tt in range(current_t, len(self.availability[r])):
                    if self.availability[r][tt]:
                        streak += 1
                    else:
                        break
                if streak > max_streak:
                    max_streak = streak
                    best_r = r

        if best_r != -1:
            self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            # No spot anywhere, use ON_DEMAND
            return ClusterType.ON_DEMAND