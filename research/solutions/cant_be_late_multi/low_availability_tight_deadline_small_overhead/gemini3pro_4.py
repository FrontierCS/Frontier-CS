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
        
        Strategy:
        1. Calculate slack (time remaining - work remaining).
        2. If slack is critically low ("Panic Mode"), force On-Demand to guarantee completion.
        3. If slack is sufficient:
           - If Spot is available in current region, use it.
           - If Spot is unavailable, switch to next region and wait (NONE) to check availability next step,
             provided we have enough slack to afford the search time.
        """
        # Calculate current state
        done_work = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done_work)
        
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        gap = self.env.gap_seconds
        
        # Panic Threshold Calculation
        # We need enough time to finish remaining work plus overheads.
        # Buffer includes:
        # - restart_overhead: In case we need to start/restart now.
        # - 2.5 * gap: Safety margin for step quantization and one potential last-minute failure.
        panic_threshold = self.restart_overhead + 2.5 * gap
        
        # 1. Safety Check (Panic Mode)
        # If time is running out, strictly use On-Demand to avoid missing the deadline (-100k penalty).
        if time_remaining < remaining_work + panic_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Try Spot Instance
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Spot Unavailable Locally - Search Strategy
        # If we can afford to waste one time step searching for a better region, do it.
        # We check if we'll still be safe after losing 'gap' seconds.
        if time_remaining - gap >= remaining_work + panic_threshold:
            # Switch to the next region (cyclical search)
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Return NONE to avoid cost while checking the new region's status in the next step.
            return ClusterType.NONE
            
        # 4. Fallback: No Spot and Cannot Search
        # We are not in full panic yet, but don't have enough slack to waste time searching.
        return ClusterType.ON_DEMAND