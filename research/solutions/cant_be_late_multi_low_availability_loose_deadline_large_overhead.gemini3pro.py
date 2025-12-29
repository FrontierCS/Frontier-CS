import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "robust_search_strategy"  # REQUIRED: unique identifier

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
        
        # Calculate slack: the amount of time we can afford to waste/wait
        slack = time_remaining - work_remaining
        
        # Define safety buffer to guarantee completion using On-Demand.
        # We need to preserve enough slack to cover:
        # 1. The current timestep (potentially lost if we search/wait)
        # 2. The restart overhead required to start an On-Demand instance
        # 3. A safety margin for robustness
        safety_buffer = (1.5 * self.env.gap_seconds) + (3.0 * self.restart_overhead)
        
        # 1. Panic Mode: If slack is running low, force On-Demand.
        # This guarantees completion before the deadline.
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND
            
        # 2. Prefer Spot if available in the current region.
        # This is the most cost-effective option.
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Search Mode: Spot is unavailable, but we have plenty of slack.
        # Switch to the next region to check for Spot availability.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        
        # Return NONE to pause for this timestep.
        # We cannot safely return SPOT immediately after switching because we don't 
        # know if the new region has Spot capacity (has_spot is for the old region).
        # Pausing costs 0 money (burns slack) and allows us to check status in the next step.
        return ClusterType.NONE