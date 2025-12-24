import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "solution_strategy"

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
        """
        # Calculate work progress and time constraints
        done_time = sum(self.task_done_time)
        remaining_work = self.task_duration - done_time
        elapsed_time = self.env.elapsed_seconds
        time_left = self.deadline - elapsed_time

        # Calculate pending overhead logic
        # If we switch to OD (or start it), we incur overhead unless we are already on it.
        if last_cluster_type == ClusterType.ON_DEMAND:
            current_overhead_cost = self.remaining_restart_overhead
        else:
            current_overhead_cost = self.restart_overhead

        # Panic Threshold:
        # Determine if we must switch to On-Demand to guarantee meeting the deadline.
        # We use a safety buffer to account for simulation step gaps and float precision.
        # 1800 seconds (30 mins) + 2 * gap ensures we trigger even if the step size is large.
        safety_buffer = 1800.0 + 2.0 * self.env.gap_seconds
        min_time_required = remaining_work + current_overhead_cost + safety_buffer

        if time_left < min_time_required:
            return ClusterType.ON_DEMAND

        # Strategy: Prefer Spot instances to minimize cost
        if has_spot:
            return ClusterType.SPOT

        # If Spot is unavailable in the current region, try to find it in others.
        # We switch to the next region and return NONE (wait).
        # In the next step, we will check availability in the new region.
        # This incurs a "wait" cost of 1 time step but no monetary cost.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        return ClusterType.NONE
