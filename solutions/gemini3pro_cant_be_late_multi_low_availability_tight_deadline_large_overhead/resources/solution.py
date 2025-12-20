import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostOptimizedStrategy"

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
        1. Calculate the 'Panic Threshold': The latest possible time we must switch to 
           On-Demand to guarantee completion, plus a safety buffer.
        2. If current time is past this threshold, force On-Demand.
        3. Otherwise (healthy slack), prefer Spot instances:
           - If current region has Spot, use it.
           - If not, switch to the next region and pause (NONE) to check availability next step.
        """
        # Current state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        elapsed_time = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed_time
        
        gap_seconds = self.env.gap_seconds
        full_overhead = self.restart_overhead
        
        # Calculate time required if we commit to On-Demand NOW
        # If we are already On-Demand, we only need to finish the current overhead (if any) + work
        # If we are on Spot or None, we incur the full restart overhead to switch
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_cost = self.remaining_restart_overhead
        else:
            overhead_cost = full_overhead
            
        time_needed_on_demand = work_remaining + overhead_cost
        
        # Panic Threshold Calculation
        # We need to ensure: time_remaining > time_needed_on_demand
        # We add a buffer of 1.5 * gap_seconds to handle:
        # 1. Discrete time steps (we might be mid-step)
        # 2. Safety margin against floating point issues or slight delays
        # If we wait one more step (gap_seconds), we must still be safe.
        panic_threshold = time_needed_on_demand + 1.5 * gap_seconds
        
        if time_remaining < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # If we have sufficient slack, prioritize minimizing cost (Spot)
        if has_spot:
            # Spot is available in the current region
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            # Since we have slack, we can afford to search for a better region.
            # We cycle through regions in a Round-Robin fashion.
            next_region_idx = (current_region + 1) % num_regions
            self.env.switch_region(next_region_idx)
            
            # We return NONE here because we've just switched regions.
            # We do not know if the new region has Spot available until the next step.
            # Returning SPOT blindly risks an error if the new region also lacks availability.
            # Returning NONE incurs no cost and allows us to check 'has_spot' in the next step.
            return ClusterType.NONE
