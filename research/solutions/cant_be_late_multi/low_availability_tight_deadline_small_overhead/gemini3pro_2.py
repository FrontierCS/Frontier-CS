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
        # Gather current state
        elapsed = self.env.elapsed_seconds
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        
        # If task is effectively done, stop (though env should handle this)
        if remaining_work <= 0:
            return ClusterType.NONE

        deadline = self.deadline
        time_left = deadline - elapsed
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Panic Threshold Calculation
        # We need enough time to finish work + incur at least one overhead (to start OD)
        # We add a buffer (1.5 * gap) to be safe against timing quantization/jitter
        critical_time_needed = remaining_work + overhead + (1.5 * gap)
        
        # 1. PANIC MODE: If time is tight, force On-Demand to guarantee completion.
        if time_left < critical_time_needed:
            return ClusterType.ON_DEMAND

        # 2. SPOT AVAILABLE: If current region has Spot, use it.
        # This is always preferred over OD or searching if we are not in panic mode.
        if has_spot:
            return ClusterType.SPOT

        # 3. SEARCH MODE: Spot is unavailable in current region.
        # We must decide to switch regions or fallback to OD.
        
        # If we have healthy slack, we search for Spot in other regions.
        # "Healthy slack" is defined as having a buffer significantly larger than the panic threshold.
        # We use a buffer of 4 hours (4 * gap) to allow for some search steps (NONE) without risking the deadline.
        
        safe_search_buffer = 4.0 * gap
        
        if time_left - critical_time_needed > safe_search_buffer:
            # We have enough slack to waste a step searching.
            # Switch to next region in Round-Robin fashion.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Return NONE to pause execution for this step. 
            # In the next step, we will see if 'has_spot' is True for the new region.
            return ClusterType.NONE
            
        else:
            # Slack is moderate/low. We shouldn't waste time searching (returning NONE).
            # We need to make progress.
            
            # If we are already on OD, stay on OD to avoid extra overheads.
            if self.env.cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            
            # If we are not on OD (e.g. lost Spot or just arrived), we must run.
            # Fallback to OD in current region.
            return ClusterType.ON_DEMAND