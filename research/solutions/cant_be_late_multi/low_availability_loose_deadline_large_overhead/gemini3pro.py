import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "Reactive_Region_Hopper"

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
        1. Panic Check: If deadline is approaching, force On-Demand.
        2. Spot Check: If current region has Spot, use it.
        3. Hunt: If current region has no Spot, switch to next region and wait.
        """
        # Retrieve current state
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        time_left = self.deadline - current_time

        # Calculate time required if we switch to On-Demand immediately.
        # If we are not currently on On-Demand, we assume we must pay the full restart overhead.
        overhead_cost = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_cost = self.restart_overhead
        
        # Add a safety buffer (1.5 time steps) to prevent missing the deadline due to step quantization
        # or minor timing fluctuations.
        buffer = self.env.gap_seconds * 1.5
        min_required_time = work_left + overhead_cost + buffer

        # Panic Logic: If remaining time is critically low, switch to On-Demand.
        if time_left < min_required_time:
            return ClusterType.ON_DEMAND

        # Spot Logic: If Spot is available in the current region, use it.
        # This is the most cost-effective option.
        if has_spot:
            return ClusterType.SPOT

        # Hunt Logic: Spot is unavailable in the current region.
        # Instead of waiting (which might take a long time), switch to the next region.
        # We cycle through regions in a round-robin fashion.
        num_regions = self.env.get_num_regions()
        current_region = self.env.get_current_region()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)

        # Return NONE for this step. We cannot run Spot immediately in the new region
        # because we don't know its availability until the next step.
        # Returning NONE incurs no cost (other than time passage).
        return ClusterType.NONE