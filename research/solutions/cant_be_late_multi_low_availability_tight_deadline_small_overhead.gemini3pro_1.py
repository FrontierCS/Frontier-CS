import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostAwareGreedyStrategy"

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
        
        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Panic Threshold Calculation
        # We must switch to On-Demand if the remaining time is close to the 
        # minimum required time to finish (work + restart overhead).
        # We add a buffer of 1.5 * gap to account for the discrete time steps
        # and ensure we switch before it's too late.
        panic_threshold = work_remaining + overhead + (1.5 * gap)
        
        if time_remaining < panic_threshold:
            # Not enough slack to risk Spot instances. Force On-Demand.
            return ClusterType.ON_DEMAND

        # Economy Mode
        if has_spot:
            # Spot is available, prioritize it for cost savings.
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            # Switch to next region to search for availability.
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # Since 'has_spot' corresponds to the old region, we cannot 
            # return SPOT immediately due to API constraints. 
            # Return NONE to wait one step and check the new region's availability.
            return ClusterType.NONE
