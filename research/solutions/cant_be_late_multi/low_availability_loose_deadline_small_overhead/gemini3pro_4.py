import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "cant_be_late_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
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
        Strategy:
        1. Safety First: If time is running out, force On-Demand execution to meet deadline.
        2. Economy: If safe, prefer Spot instances.
           - If current region has Spot, use it.
           - If current region lacks Spot, switch region and pause (NONE) to probe next step.
        """
        # Current status
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done

        # If task is effectively done, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        time_left = self.deadline - elapsed
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Safety Threshold Calculation
        # We need enough time to finish the work using On-Demand (guaranteed capacity).
        # Required time = remaining_work + restart_overhead (if we switch type).
        # We add a buffer of 2 * gap_seconds to account for:
        # - The discrete nature of time steps (we decide for the *next* gap)
        # - Potential overhead/transition delays
        # If we are below this threshold, we cannot risk hunting for Spot anymore.
        safety_threshold = remaining_work + overhead + 2.0 * gap

        if time_left < safety_threshold:
            return ClusterType.ON_DEMAND

        # Economy Strategy
        if has_spot:
            # Spot is available in current region, use it
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            # Switch to the next region to check its availability in the next step.
            # We return NONE (pause) because we cannot check 'has_spot' for the new region
            # in the current step, and returning SPOT blindly may cause an error.
            # This incurs a time cost of 'gap' seconds, but saves money compared to On-Demand.
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE