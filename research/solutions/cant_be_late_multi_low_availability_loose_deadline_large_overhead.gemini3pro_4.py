import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        # Calculate time and work metrics in seconds
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_needed = self.task_duration - work_done
        time_left = self.deadline - elapsed
        
        # System parameters
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # 1. Survival Check
        # We must ensure we have enough time to finish using guaranteed On-Demand instances.
        # We add a safety buffer to account for:
        # - The work remaining
        # - Potential restart overhead (switching to OD)
        # - Step quantization (gap) and margin for error
        # If time is tight, we stop optimizing for cost and force completion.
        safety_buffer = work_needed + overhead + (2.5 * gap)
        
        if time_left < safety_buffer:
            return ClusterType.ON_DEMAND
            
        # 2. Cost Optimization
        # If we have slack, we prefer Spot instances (cheaper).
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable in the current region, but we have plenty of time.
            # Strategy: Search for Spot in other regions.
            # Action: Switch to the next region and pause (NONE) for this step.
            # This incurs a time penalty (gap + overhead) but 0 monetary cost.
            # In the next step, we will check 'has_spot' for the new region.
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE
