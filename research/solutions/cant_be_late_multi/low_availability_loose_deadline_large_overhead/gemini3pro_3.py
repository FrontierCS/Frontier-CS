import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostOptimizedStrategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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
        1. Calculate remaining slack time.
        2. If slack is low (approaching point of no return), force On-Demand to guarantee completion.
        3. If slack is high:
           - If Spot is available in current region, use it (cheapest).
           - If Spot is unavailable, switch to the next region and wait (NONE) one step to probe availability.
             (Using NONE consumes slack but saves money compared to On-Demand).
        """
        # 1. State Assessment
        elapsed = self.env.elapsed_seconds
        done_time = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done_time)
        
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - elapsed
        
        # 2. Safety Calculation
        # Calculate time required to finish if we switch to/continue with On-Demand.
        # If we are not currently on On-Demand, assume worst-case restart overhead.
        current_overhead = self.remaining_restart_overhead
        
        if last_cluster_type == ClusterType.ON_DEMAND:
            time_needed = remaining_work + current_overhead
        else:
            time_needed = remaining_work + self.restart_overhead

        # Define safety buffer. 
        # We need enough buffer to absorb:
        # - The current time step size (gap_seconds)
        # - Quantization effects
        # - A safety margin (e.g., 2.5 hours) to prevent missing the hard deadline.
        #   9000s = 2.5 hours.
        safety_buffer = 9000.0 + 2.0 * self.env.gap_seconds

        # 3. Decision Logic
        
        # Panic Mode: If time is tight, we must use On-Demand.
        if time_left < (time_needed + safety_buffer):
            return ClusterType.ON_DEMAND

        # Economy Mode: We have plenty of time.
        if has_spot:
            # Spot is available here. Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in this region.
            # Strategy: Search other regions.
            # Switching regions incurs 'restart_overhead' cost (time only, if we use NONE).
            # We switch and return NONE to "probe" the new region in the next tick.
            
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                current_region = self.env.get_current_region()
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
                return ClusterType.NONE
            else:
                # If only one region exists and no spot, we wait (NONE) to save money 
                # until panic mode triggers On-Demand.
                return ClusterType.NONE