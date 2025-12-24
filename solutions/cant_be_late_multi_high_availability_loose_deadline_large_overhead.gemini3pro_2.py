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
        
        Strategy:
        1. Calculate the latest possible time we must start On-Demand to meet the deadline ("Panic Mode").
           If we are close to this threshold, force On-Demand to guarantee success.
        2. If we have slack, prioritize Spot instances to minimize cost.
        3. If Spot is unavailable in the current region, switch to a new region (Round-Robin) and wait.
        """
        # --- State Retrieval ---
        elapsed = self.env.elapsed_seconds
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        remaining_time = self.deadline - elapsed
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # --- Panic Mode Calculation ---
        # We must ensure we can finish the task using On-Demand (OD) even if we waste the current step.
        # Time required to finish on OD = remaining_work + overhead (assuming a restart is needed).
        # We need a safety buffer because decisions are made in discrete 'gap' steps.
        # If we try Spot and fail, we lose 'gap' seconds.
        # Therefore, we must switch to OD if:
        # remaining_time - gap < remaining_work + overhead
        # Using a 1.5x gap buffer for safety against floating point issues and tight bounds.
        panic_threshold = remaining_work + overhead + (gap * 1.5)
        
        if remaining_time < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # --- Cost Optimization (Spot) ---
        if has_spot:
            # Spot is available and we have slack. Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            # Strategy: Switch to the next region to explore availability.
            # We use Round-Robin to cycle through all regions.
            current_region_idx = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region_idx = (current_region_idx + 1) % num_regions
            
            self.env.switch_region(next_region_idx)
            
            # We cannot run Spot immediately in the new region in this step 
            # (state reflects old region). Return NONE to process the switch.
            return ClusterType.NONE
