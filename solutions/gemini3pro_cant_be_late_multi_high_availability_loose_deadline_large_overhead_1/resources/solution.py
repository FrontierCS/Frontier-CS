import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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
        # Calculate remaining work
        done_work = sum(self.task_done_time)
        left_work = self.task_duration - done_work
        
        # If work is effectively done, stop
        if left_work <= 1e-6:
            return ClusterType.NONE
            
        elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed
        pending_overhead = self.remaining_restart_overhead
        
        # Calculate slack: How much extra time we have versus required work + current recovery
        slack = time_remaining - (left_work + pending_overhead)
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Safety buffer:
        # We need enough time to handle:
        # 1. The current step gap (if we wait)
        # 2. A potential restart overhead if we switch to On-Demand
        # 3. A safety margin (2.0 factor on gap)
        buffer = 2.0 * gap + 2.0 * overhead
        
        # CRITICAL: If slack is low, force On-Demand to guarantee meeting the deadline
        if slack < buffer:
            return ClusterType.ON_DEMAND
            
        # If we have slack and Spot is available, use it (cheapest option)
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable but we have slack:
        # Switch to the next region and wait (NONE) to check its availability in the next step.
        # Returning NONE avoids paying for On-Demand while searching.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        return ClusterType.NONE
