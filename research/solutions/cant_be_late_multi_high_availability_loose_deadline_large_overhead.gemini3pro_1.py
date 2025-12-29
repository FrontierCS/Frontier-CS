import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """cant_be_late_strategy"""

    NAME = "cant_be_late_strategy"

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
        1. Calculate remaining time and work.
        2. If time is running out (Panic Mode), force On-Demand to guarantee completion.
        3. If Spot is available in current region, use it (cheapest).
        4. If Spot is unavailable, switch to the next region and wait (ClusterType.NONE).
           This avoids paying On-Demand costs while "probing" for Spot availability in other regions.
        """
        # Calculate progress
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        
        # If work is completed, pause (though environment usually stops automatically)
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        
        # Safety Buffer Calculation
        # We need enough time to:
        # 1. Complete the remaining work
        # 2. Pay the restart overhead (if we switch to OD)
        # 3. Buffer for step quantization (gap_seconds) to ensure we don't miss by a fraction of a step
        # Using 2.0 * gap_seconds as a safe margin.
        buffer_seconds = 2.0 * self.env.gap_seconds
        time_needed_for_safe_finish = remaining_work + self.restart_overhead + buffer_seconds
        
        # 1. Panic Mode: Deadline approaching
        if time_left < time_needed_for_safe_finish:
            return ClusterType.ON_DEMAND

        # 2. Optimization Mode
        if has_spot:
            # Spot is available here, use it to minimize cost
            return ClusterType.SPOT
        else:
            # Spot is not available in the current region.
            # We have slack (time_left > time_needed), so we can afford to search for a better region.
            # Switch to the next region in a round-robin fashion.
            current_region_idx = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region_idx = (current_region_idx + 1) % num_regions
            
            self.env.switch_region(next_region_idx)
            
            # Return NONE for this step.
            # This incurs no monetary cost (unlike checking with ON_DEMAND).
            # In the next step, 'has_spot' will reflect the availability in the new region.
            return ClusterType.NONE