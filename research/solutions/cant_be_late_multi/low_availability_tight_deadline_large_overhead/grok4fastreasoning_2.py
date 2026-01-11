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
        for path in trace_files:
            try:
                with open(path, 'r') as tf:
                    data = json.load(tf)
                    avail = data.get("availability", [])
                    self.availability.append(avail)
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                self.availability.append([])

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
        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        t = int(elapsed // gap)
        current_r = self.env.get_current_region()
        num_r = self.env.get_num_regions()

        # Use SPOT if available in current region
        if has_spot:
            return ClusterType.SPOT

        # Check other regions for current timestep spot availability
        for r in range(num_r):
            if r == current_r:
                continue
            if t < len(self.availability[r]) and self.availability[r][t]:
                self.env.switch_region(r)
                return ClusterType.SPOT

        # No spot available anywhere, fall back to ON_DEMAND
        return ClusterType.ON_DEMAND