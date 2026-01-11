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

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Current state variables
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_left = self.deadline - elapsed
        
        # Parameters
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Safety buffer calculation
        # We need a buffer to ensure we can finish on On-Demand even in worst case.
        # Buffer includes:
        # 1. Restart overhead (potentially incurred if we switch to OD or regions)
        # 2. Granularity buffer (2.5 steps) to account for step sizes and floating point variances
        safety_buffer = overhead + (2.5 * gap)
        
        # Condition 1: Panic Threshold
        # If remaining time is tight, force On-Demand to guarantee completion.
        # On-Demand is reliable (never interrupted) but expensive.
        # We prioritize meeting the deadline over cost here.
        if time_left < (remaining_work + safety_buffer):
            return ClusterType.ON_DEMAND

        # Condition 2: Use Spot if available
        # If we have slack, Spot is the preferred cheap option.
        if has_spot:
            return ClusterType.SPOT

        # Condition 3: Spot unavailable, but we have slack
        # Strategy: Switch to the next region and wait one step to check availability.
        # This incurs overhead (region switch) + wait time (gap), but allows us to
        # search for cheaper resources when we are not pressed for time.
        
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Cycle to next region
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        # Return NONE to pause for this step. 
        # We cannot return SPOT immediately after switching because we don't know 
        # the availability of the new region until the next step.
        return ClusterType.NONE