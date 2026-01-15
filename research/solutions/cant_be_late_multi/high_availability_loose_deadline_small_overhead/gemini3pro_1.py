import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "robust_switcher"

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
        Prioritizes minimizing cost using Spot instances while maintaining a safety buffer
        to guarantee meeting the deadline using On-Demand if necessary.
        """
        # Calculate current progress and time constraints
        done_time = sum(self.task_done_time)
        remaining_work = self.task_duration - done_time
        current_time = self.env.elapsed_seconds
        remaining_time = self.deadline - current_time
        
        # System parameters
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Define Safety Margin
        # We must ensure we have enough time to finish remaining work on On-Demand.
        # We add a buffer for:
        # 1. Overhead: Incurred if we need to start/restart the On-Demand instance.
        # 2. Step Granularity (Gap): To avoid deadline misses due to discrete time steps.
        # Margin = Overhead + 1.5 * Gap
        safety_margin = overhead + (gap * 1.5)
        
        # Critical Slack Check
        # If we are nearing the deadline, we must use On-Demand to guarantee completion.
        if remaining_time < (remaining_work + safety_margin):
            return ClusterType.ON_DEMAND
            
        # Cost Minimization Logic
        if has_spot:
            # Spot is available and we have slack. Use it to save money.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in the current region.
            # We must decide whether to switch regions or fall back to On-Demand.
            
            # Switching Region Costs:
            # 1. Overhead (restart penalty).
            # 2. Time lost during the transition (we return NONE for one step to safely check new availability).
            # Total Time Cost Estimate = Overhead + Gap
            
            switch_time_cost = overhead + gap
            
            # Check if we have enough slack to afford the switch attempt
            # We need: Remaining Time > Remaining Work + Safety Margin + Switch Cost
            if remaining_time > (remaining_work + safety_margin + switch_time_cost):
                n_regions = self.env.get_num_regions()
                if n_regions > 1:
                    # Switch to the next region in a round-robin cycle
                    curr_idx = self.env.get_current_region()
                    next_idx = (curr_idx + 1) % n_regions
                    self.env.switch_region(next_idx)
                    
                    # Return NONE to pause execution for this step.
                    # This incurs no monetary cost and allows us to check 'has_spot' 
                    # for the new region in the next step.
                    return ClusterType.NONE
                else:
                    # Single region environment, cannot switch.
                    return ClusterType.ON_DEMAND
            else:
                # Not enough slack to hunt for Spot. Force On-Demand.
                return ClusterType.ON_DEMAND