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

        # Preload availability traces
        self.gap_seconds = self.env.gap_seconds
        self.num_regions = self.env.get_num_regions()
        self.trace_files = config["trace_files"]
        self.availability: List[List[bool]] = []
        for path in self.trace_files:
            with open(path, 'r') as f:
                avail = json.load(f)
                if avail and isinstance(avail[0], int):
                    avail = [bool(x) for x in avail]
                self.availability.append(avail)

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
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        if remaining_work <= 0:
            return ClusterType.NONE

        current_step = int(self.env.elapsed_seconds // self.gap_seconds)
        current_region = self.env.get_current_region()

        # Find regions with spot available this step
        spot_regions = [
            r for r in range(self.num_regions)
            if current_step < len(self.availability[r]) and self.availability[r][current_step]
        ]

        if not spot_regions:
            # No spot anywhere, use on-demand
            return ClusterType.ON_DEMAND

        # Prefer spot
        if last_cluster_type == ClusterType.SPOT:
            # Can switch freely
            target = spot_regions[0]
            if target != current_region:
                self.env.switch_region(target)
            return ClusterType.SPOT
        else:
            # Type change needed, prefer current if possible
            if has_spot and current_step < len(self.availability[current_region]) and self.availability[current_region][current_step]:
                # Stay and switch to spot
                return ClusterType.SPOT
            else:
                # Switch to a spot region and switch to spot
                target = spot_regions[0]
                self.env.switch_region(target)
                return ClusterType.SPOT