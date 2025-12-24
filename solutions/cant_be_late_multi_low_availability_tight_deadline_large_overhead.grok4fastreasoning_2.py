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

        self.num_regions = self.env.get_num_regions()
        self.scouting = True
        self.scout_duration = 1800.0  # 30 minutes per region
        self.scout_regions = list(range(self.num_regions))
        self.current_scout_idx = 0
        self.scout_elapsed = [0.0] * self.num_regions
        self.visits = [0] * self.num_regions
        self.total_spot = [0] * self.num_regions

        # Start scouting from first region
        first_r = self.scout_regions[0]
        self.env.switch_region(first_r)
        self.scout_elapsed[first_r] = 0.0

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
        region = self.env.get_current_region()

        # Record observation for current region
        self.visits[region] += 1
        if has_spot:
            self.total_spot[region] += 1

        # Compute total progress
        total_progress: float = sum(self.task_done_time)
        remaining_work = self.task_duration - total_progress
        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        est_needed = remaining_work + self.remaining_restart_overhead

        # If time is tight, stop scouting and run conservatively
        if time_left < est_needed * 1.1:
            if self.scouting:
                # Pick best based on current data
                rates = [self.total_spot[i] / max(1, self.visits[i]) for i in range(self.num_regions)]
                best_r = rates.index(max(rates))
                self.env.switch_region(best_r)
                self.scouting = False

            # Run, prefer SPOT if safe
            if has_spot and time_left > remaining_work + self.restart_overhead:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # Normal operation
        if not self.scouting:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # Scouting phase
        cluster = ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
        self.scout_elapsed[region] += self.env.gap_seconds

        if self.scout_elapsed[region] >= self.scout_duration:
            self.current_scout_idx += 1
            if self.current_scout_idx < self.num_regions:
                next_r = self.scout_regions[self.current_scout_idx]
                self.env.switch_region(next_r)
                self.scout_elapsed[next_r] = 0.0
            else:
                # Scouting complete, pick best region
                rates = [self.total_spot[i] / max(1, self.visits[i]) for i in range(self.num_regions)]
                best_r = rates.index(max(rates))
                self.env.switch_region(best_r)
                self.scouting = False

        return cluster
