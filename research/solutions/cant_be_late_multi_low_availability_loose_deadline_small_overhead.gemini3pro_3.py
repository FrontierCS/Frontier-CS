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
        )
        super().__init__(args)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Calculate current state
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        total_work = self.task_duration
        remaining_work = total_work - done
        
        # Check if work is already done (handling float precision)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        remaining_time = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate panic threshold.
        # We switch to ON_DEMAND if time is running out.
        # Buffer required:
        # 1. remaining_work: Time needed to execute code.
        # 2. switch_overhead: Time needed to spin up OD (if not already running).
        # 3. gap: To account for the granularity of the current step (safety margin).
        
        switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead
        panic_threshold = remaining_work + switch_overhead + 1.1 * gap
        
        # If we are close to the deadline, force On-Demand to guarantee completion.
        if remaining_time < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # Normal operation: Prefer Spot to save costs
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is not available in the current region.
            # Since we have slack (not in panic mode), we search for Spot in other regions.
            # Switch to the next region and return NONE (pause) for this step.
            # The availability in the new region will be checked in the next step.
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            return ClusterType.NONE