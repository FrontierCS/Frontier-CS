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
        # Retrieve environment state
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        total_work = self.task_duration
        work_remaining = max(0.0, total_work - work_done)
        
        deadline = self.deadline
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate time remaining until deadline
        time_left = deadline - current_time
        
        # Calculate minimum time needed to complete the task on a reliable instance (On-Demand),
        # including potential restart overhead. We assume the worst case (full overhead).
        time_needed_for_completion = work_remaining + overhead
        
        # Safety buffer to account for step granularity (gap_seconds).
        # We need a margin to ensure we don't cross the deadline boundary while searching for Spot.
        # 3.0 * gap provides a robust buffer.
        safety_buffer = 3.0 * gap
        
        # 1. Critical Deadline Check
        # If we are close to the deadline, we must use On-Demand to guarantee completion.
        if time_left < (time_needed_for_completion + safety_buffer):
            return ClusterType.ON_DEMAND

        # 2. Cost Optimization (Slack exists)
        if has_spot:
            # If Spot is available in the current region, use it (cheapest option).
            return ClusterType.SPOT
        else:
            # Spot is not available in the current region.
            # Since we have slack, we hunt for Spot in other regions.
            
            num_regions = self.env.get_num_regions()
            
            if num_regions > 1:
                # Switch to the next region (Round-Robin).
                current_region = self.env.get_current_region()
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
                
                # Return NONE to pause execution for this step.
                # We consume 'gap' time to move to the new region and check availability
                # in the next step.
                return ClusterType.NONE
            else:
                # Only one region exists and it has no Spot.
                # Wait (NONE) and hope for Spot availability, as waiting is cheaper than On-Demand.
                return ClusterType.NONE
