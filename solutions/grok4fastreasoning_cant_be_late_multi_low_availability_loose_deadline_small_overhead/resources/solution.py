import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "learning_cycle"

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
        current_progress = sum(self.task_done_time)
        if current_progress >= self.task_duration:
            return ClusterType.NONE

        if not hasattr(self, 'visits'):
            num_regions = self.env.get_num_regions()
            self.visits = [0] * num_regions
            self.spot_success = [0] * num_regions

        cur = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        self.visits[cur] += 1
        self.spot_success[cur] += 1 if has_spot else 0

        elapsed = self.env.elapsed_seconds
        remaining_overhead = self.remaining_restart_overhead
        time_left = self.deadline - elapsed - remaining_overhead
        if time_left <= 0:
            return ClusterType.NONE

        remaining_work = self.task_duration - current_progress
        gap = self.env.gap_seconds
        estimated_steps = time_left / gap
        urgent = remaining_work > estimated_steps * gap * 0.95

        if has_spot:
            return ClusterType.SPOT
        elif urgent:
            return ClusterType.ON_DEMAND
        else:
            # Find best region to switch to
            best_r = -1
            best_rate = -1.0
            for r in range(num_regions):
                if r == cur:
                    continue
                v = self.visits[r]
                s = self.spot_success[r]
                rate = s / v if v > 0 else 0.5
                if rate > best_rate or (rate == best_rate and (best_r == -1 or r < best_r)):
                    best_rate = rate
                    best_r = r
            if best_r != -1:
                self.env.switch_region(best_r)
            return ClusterType.ON_DEMAND
