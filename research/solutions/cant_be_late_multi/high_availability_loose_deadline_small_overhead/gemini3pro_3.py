import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cost_optimized_strategy"

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
        """
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Calculate time needed for guaranteed completion using On-Demand.
        # We include restart overhead to be conservative, as we might need to start/switch.
        time_needed_for_od = work_remaining + self.restart_overhead
        
        # Calculate slack: the amount of time we can afford to "waste" (waiting/searching)
        # before we must commit to On-Demand to meet the deadline.
        slack = time_remaining - time_needed_for_od
        
        # Safety buffer in seconds (4 hours).
        # If slack falls below this threshold, we switch to On-Demand immediately to ensure
        # we finish before the deadline. A 4-hour buffer handles large time steps and ensures
        # we have margin for the final run.
        safety_buffer = 4.0 * 3600.0

        # Panic Logic: If we are running out of time, force On-Demand.
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND

        # Standard Logic: Try to use Spot instances to save cost.
        if has_spot:
            # If Spot is available in the current region, use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            # Since we have sufficient slack, we search for Spot in other regions.
            
            # Switch to the next region in a round-robin fashion.
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # We return NONE because we do not know the availability of the new region yet.
            # Returning SPOT blindly risks an error if the new region also lacks Spot.
            # Returning NONE incurs no monetary cost (only time), which we can afford given the slack.
            return ClusterType.NONE