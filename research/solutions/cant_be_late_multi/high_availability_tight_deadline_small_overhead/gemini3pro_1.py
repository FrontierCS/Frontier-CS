import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "robust_cost_optimizer"

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
        Prioritize Spot instances to minimize cost, but switch to On-Demand
        when the deadline approaches (Panic Mode).
        If Spot is unavailable in the current region and slack permits, 
        switch regions to search for Spot.
        """
        # 1. Update Progress
        current_work = sum(self.task_done_time)
        remaining_work = self.task_duration - current_work
        
        # 2. Check Time Constraints
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate minimum time needed to finish using On-Demand (safe path).
        # needed = work + overhead (worst case for restart/switch).
        time_needed_od = remaining_work + overhead
        
        # Safety Buffer:
        # We need a buffer to account for step granularity (gap_seconds) and 
        # ensure we don't accidentally cross the deadline.
        # 3.0 * gap provides a robust margin (e.g., 3 hours if gap is 1h).
        # If remaining slack drops below this buffer, we force OD.
        buffer = 3.0 * gap
        
        # 3. Decision Logic
        
        # PANIC MODE: Not enough time to risk searching or Spot interruptions.
        if time_left < time_needed_od + buffer:
            return ClusterType.ON_DEMAND

        # NORMAL MODE: Try to use Spot.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            # Since we are not in panic mode, we have slack to "hunt" for Spot.
            # Strategy: Switch to next region and wait 1 step (NONE) to check availability.
            # We accept the time cost of NONE (gap_seconds) to save money.
            
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # We must return NONE here because:
            # 1. We cannot return SPOT (has_spot is False for the call).
            # 2. Returning ON_DEMAND defeats the purpose of searching (high cost).
            return ClusterType.NONE