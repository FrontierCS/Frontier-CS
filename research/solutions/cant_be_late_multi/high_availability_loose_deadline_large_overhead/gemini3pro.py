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
        Strategy:
        1. Check if we are close to the deadline (Panic Mode). If so, force ON_DEMAND to guarantee completion.
        2. If we have slack, prefer SPOT.
        3. If SPOT is unavailable in current region, switch to next region and wait (NONE) to probe availability.
        """
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If task is effectively done, return NONE
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed

        # Panic Threshold Calculation
        # We need 'work_remaining' time to finish using On-Demand (which is guaranteed).
        # We add 'restart_overhead' because switching to OD or recovering might incur overhead.
        # We add a 2-hour (7200s) buffer for safety against time step granularity and small delays.
        # This ensures we switch to OD with ample time to finish.
        safety_threshold = work_remaining + self.restart_overhead + 7200.0

        # If strictly limited time remains, force On-Demand execution
        if time_left < safety_threshold:
            return ClusterType.ON_DEMAND

        # Opportunistic Strategy (Cost Minimization)
        if has_spot:
            # If Spot is available in the current region, use it
            return ClusterType.SPOT
        else:
            # If Spot is unavailable, and we have slack time (not in panic mode):
            # Strategy: Switch to the next region (Round-Robin) and wait one step (NONE).
            # This allows us to "probe" the availability of the new region in the next time step.
            # While this burns one time step, it avoids paying for On-Demand when we have time to search.
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE