import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cost-aware multi-region scheduling strategy."""

    NAME = "cost_optimized_strategy"

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
        Priority: 
        1. Meet deadline (Panic Mode -> On-Demand).
        2. Minimize cost (Economy Mode -> Spot).
        3. Search for Spot (Economy Mode -> Switch Region + None).
        """
        # Current state
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        work_remaining = self.task_duration - done
        time_left = self.deadline - elapsed
        
        # System parameters
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate safety buffer
        # We need time for:
        # 1. Remaining work
        # 2. Potential restart overhead (to switch to On-Demand)
        # 3. Buffer for quantization (gap size) and safety margin
        # If we return NONE this step to search, we lose 'gap' seconds. 
        # So we must ensure (time_left - gap) is still safe.
        required_time = work_remaining + overhead
        safety_buffer = (2.0 * gap) + (2.0 * overhead)
        
        # Panic Mode: If we are close to the point of no return, use On-Demand
        if time_left < (required_time + safety_buffer):
            return ClusterType.ON_DEMAND
            
        # Economy Mode: We have slack time
        if has_spot:
            # Cheapest option available in current region
            return ClusterType.SPOT
        else:
            # Spot not available in current region.
            # Strategy: Switch to next region and pause (NONE) to verify availability next step.
            # Using NONE costs $0 (time only), whereas ON_DEMAND costs $$. 
            # Since we have slack, we save money by searching.
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            
            # Round-robin search
            next_region = (curr_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Return NONE to avoid paying for On-Demand while searching/switching
            return ClusterType.NONE