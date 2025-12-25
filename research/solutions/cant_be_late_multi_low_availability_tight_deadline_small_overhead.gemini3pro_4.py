import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CantBeLateStrategy"

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
        1. Calculate 'slack': extra time available beyond what is needed to finish using guaranteed On-Demand.
        2. If slack is low (Panic Mode), force On-Demand to guarantee meeting deadline.
        3. If slack is high (Safe Mode):
           - If Spot available: Use Spot (cheapest).
           - If Spot unavailable: Switch region and wait (NONE) to hunt for Spot elsewhere.
        """
        # 1. Update progress
        current_work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - current_work_done
        
        # If finished, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE

        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # 2. Calculate projected time to finish if we switch to On-Demand immediately.
        #    If we are already on OD, we just finish the current overhead (if any) + work.
        #    If not on OD, we incur the full restart overhead + work.
        overhead_cost = 0.0
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_cost = self.remaining_restart_overhead
        else:
            overhead_cost = self.restart_overhead
            
        time_needed_od = remaining_work + overhead_cost
        
        # Slack is the safety buffer.
        slack = time_remaining - time_needed_od
        
        # Define Panic Threshold.
        # We need a buffer strictly larger than gap_seconds because decisions are discrete.
        # If we attempt Spot or hunt (NONE) and fail/wait, we lose 'gap_seconds' of time.
        # We use 2.5x gap as a robust safety margin.
        panic_buffer = 2.5 * self.env.gap_seconds
        
        # 3. Decision Logic
        if slack < panic_buffer:
            # Panic Mode: Deadline is approaching. Must use On-Demand.
            # Staying in current region avoids additional region-switch overheads/delays.
            return ClusterType.ON_DEMAND
        
        # Safe Mode: optimize for cost
        if has_spot:
            # Cheapest option
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region. Hunt for Spot.
            # Strategy: Switch to next region and pause (NONE) for this step.
            # In the next step, we'll check if the new region has Spot.
            # This 'wastes' one gap_seconds period but avoids OD cost while slack permits.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE
