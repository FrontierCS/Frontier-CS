import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_strategy"

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
        # Environment parameters
        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        
        # Task progress
        work_done = sum(self.task_done_time)
        work_needed = self.task_duration - work_done
        
        # If task is effectively complete
        if work_needed <= 1e-6:
            return ClusterType.NONE

        time_remaining = deadline - elapsed
        current_overhead = self.remaining_restart_overhead
        
        # Calculate strict time needed to finish if we use On-Demand (guaranteed capacity)
        # We must account for the work itself plus any pending restart overhead
        time_needed_od = work_needed + current_overhead
        
        # Define safety buffer
        # We need a buffer to absorb the granularity of time steps (gap) and potential overheads.
        # If remaining slack falls below this buffer, we must switch to OD to guarantee deadline.
        # 1.2 * gap ensures we catch the condition at least one step before critical failure.
        safety_buffer = (gap * 1.2) + restart_overhead
        
        # 1. Deadline Safety Check (Panic Mode)
        # If we are close to the deadline, force On-Demand usage.
        if time_remaining < time_needed_od + safety_buffer:
            return ClusterType.ON_DEMAND
            
        # 2. Cost Optimization Mode
        if has_spot:
            # If Spot is available in current region, use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region, but we have enough slack (passed safety check).
            # Strategy: Switch to the next region to hunt for Spot capacity.
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            
            # Round-robin switching
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Return NONE to pause execution for this step.
            # We cannot return SPOT immediately because we don't know the new region's availability yet.
            # This burns 'gap' time but saves cost compared to running OD while probing.
            return ClusterType.NONE