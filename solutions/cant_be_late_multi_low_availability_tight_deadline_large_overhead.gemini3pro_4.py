import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "AdaptiveMultiRegionStrategy"

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
        1. Calculate remaining slack time.
        2. If slack is critically low, force ON_DEMAND to meet deadline.
        3. If slack is sufficient and Spot is available, use SPOT.
        4. If Spot is unavailable, switch to next region and wait (NONE) to probe availability.
        """
        # Calculate work remaining
        work_done = sum(self.task_done_time)
        work_needed = self.task_duration - work_done

        # If task is essentially done, stop
        if work_needed <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Safety Threshold Calculation:
        # We need enough time to:
        # 1. Complete the remaining work (work_needed)
        # 2. Pay the restart overhead if we are forced to switch/start now (overhead)
        # 3. Absorb the time cost of the current decision step (gap)
        # 4. Provide a small buffer for safety (0.5 * gap)
        # If remaining time is below this threshold, we cannot afford to hunt or wait.
        safety_threshold = work_needed + overhead + (1.5 * gap)

        if remaining_time < safety_threshold:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is not available in current region, but we have time to hunt.
            # Switch to next region in Round-Robin fashion.
            # We must return NONE (or OD) because we cannot select SPOT blindly for a new region.
            # Returning NONE minimizes cost while we probe the new region.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE
