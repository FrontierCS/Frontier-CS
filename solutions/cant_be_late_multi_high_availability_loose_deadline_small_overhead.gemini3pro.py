import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        # Calculate state
        current_work = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - current_work)
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed

        # Parameters
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Safety Logic:
        # Determine if we must switch to On-Demand to meet the deadline.
        # We need enough time for:
        # 1. The remaining work.
        # 2. The restart overhead (incurred if we switch/start OD).
        # 3. A safety buffer to handle discrete time steps (gaps) and small variations.
        #    If gap is large, we need a larger buffer to avoid missing the decision window.
        #    Buffer = 3 * gap + overhead covers the worst case of just missing a step plus overhead.
        
        safety_buffer = (3.0 * gap) + overhead
        time_needed_for_od = remaining_work + overhead
        
        if time_left < time_needed_for_od + safety_buffer:
            return ClusterType.ON_DEMAND

        # Cost Optimization Logic:
        if has_spot:
            # If Spot is available in the current region, use it.
            return ClusterType.SPOT
        else:
            # If Spot is unavailable, try other regions.
            # Strategy: Switch to the next region and 'probe' (return NONE).
            # Returning NONE incurs no cost but advances time by 'gap'.
            # In the next step, 'has_spot' will reflect the new region's availability.
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                current_region = self.env.get_current_region()
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
            
            # Wait one step to check availability in the (possibly new) region
            return ClusterType.NONE
