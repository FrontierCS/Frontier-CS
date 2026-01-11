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

        trace_paths = config["trace_files"]
        self.availability: List[List[bool]] = []
        self.num_regions = len(trace_paths)
        for path in trace_paths:
            with open(path, 'r') as f:
                data = json.load(f)
                avail = [bool(x) for x in data["availability"]]
                self.availability.append(avail)

        if self.num_regions > 0:
            spot_counts = [sum(avail) for avail in self.availability]
            self.best_region = spot_counts.index(max(spot_counts))
            self.T = len(self.availability[0])
        else:
            self.best_region = 0
            self.T = 0

        self.switched = False

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

        current_r = self.env.get_current_region()
        t_idx = min(int(self.env.elapsed_seconds // self.env.gap_seconds), self.T - 1)

        if not self.switched and current_r != self.best_region and t_idx < self.T:
            self.env.switch_region(self.best_region)
            self.switched = True
            if self.availability[self.best_region][t_idx]:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND