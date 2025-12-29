import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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
            trace_files=config.get("trace_files", [])
        )
        super().__init__(args)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Calculate remaining work
        # task_done_time is a list of work duration completed in previous steps
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If work is finished, stop (though env should handle this)
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate time remaining to deadline
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed

        # Constants
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # Safety Threshold Calculation
        # We need to ensure we have enough time to finish using On-Demand (reliable).
        # Minimum time needed = Remaining Work + Restart Overhead (if we start fresh).
        # We add a buffer of 1.5 * gap_seconds to safeguard against boundary conditions
        # and ensure we switch to OD before it's too late.
        safety_threshold = work_remaining + overhead + (1.5 * gap)

        # Panic Mode: If time is tight, force On-Demand to guarantee completion
        if time_remaining < safety_threshold:
            return ClusterType.ON_DEMAND

        # Economy Mode: Prefer Spot
        if has_spot:
            # Spot is available in the current region
            return ClusterType.SPOT
        else:
            # Spot is unavailable in the current region.
            # Strategy: Switch to the next region and probe.
            # We iterate regions in a round-robin fashion.
            # We return NONE (pause) for this step because we cannot guarantee 
            # Spot availability in the new region immediately without checking next step, 
            # and returning SPOT on an unavailable region causes an error.
            
            num_regions = self.env.get_num_regions()
            current_region_idx = self.env.get_current_region()
            
            # Switch to next region
            next_region_idx = (current_region_idx + 1) % num_regions
            self.env.switch_region(next_region_idx)
            
            return ClusterType.NONE