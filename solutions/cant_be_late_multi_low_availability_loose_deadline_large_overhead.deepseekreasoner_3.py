import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "spot_first_with_safety"

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
        
        # Initialize strategy state
        self.spot_price = 0.9701
        self.on_demand_price = 3.06
        self.spot_preference = True
        self.safety_margin_factor = 1.5
        self.region_history = {}
        self.current_region = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Calculate remaining work and time
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration[0] - completed_work
        elapsed_time = self.env.elapsed_seconds
        time_left = self.deadline[0] - elapsed_time
        
        # If no work left, do nothing
        if remaining_work <= 1e-9:
            return ClusterType.NONE
            
        # Check if we can still finish on time with on-demand
        # Considering restart overhead if switching
        effective_restart = self.restart_overhead[0] if last_cluster_type != ClusterType.ON_DEMAND else 0
        min_time_to_finish_on_demand = remaining_work + effective_restart
        
        # Emergency mode: must use on-demand to finish on time
        if time_left < min_time_to_finish_on_demand * self.safety_margin_factor:
            # Switch to on-demand if not already
            if last_cluster_type != ClusterType.ON_DEMAND:
                # Check if we need to wait for restart overhead to finish
                if self.remaining_restart_overhead[0] > 0:
                    return ClusterType.NONE
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        # If spot is available and we're in spot-preferred mode
        if has_spot and self.spot_preference:
            # If currently in spot or none, continue with spot
            if last_cluster_type in (ClusterType.SPOT, ClusterType.NONE):
                # Check if we're in restart overhead
                if self.remaining_restart_overhead[0] > 0:
                    return ClusterType.NONE
                return ClusterType.SPOT
            # If switching from on-demand to spot, consider cost-benefit
            elif last_cluster_type == ClusterType.ON_DEMAND:
                # Only switch if we have enough time buffer
                if time_left > remaining_work * 2:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        # No spot available in current region
        elif not has_spot and self.spot_preference:
            # Try to switch to another region to find spot
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            
            # Try next regions in circular order
            for offset in range(1, num_regions):
                next_region = (current_region + offset) % num_regions
                # Simple strategy: switch to next region
                self.env.switch_region(next_region)
                # After switching, we need a restart
                # Return NONE to avoid immediate work after switch
                return ClusterType.NONE
        
        # If we get here and spot is not preferred or not available,
        # use on-demand if we're not in restart overhead
        if self.remaining_restart_overhead[0] <= 0:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE
