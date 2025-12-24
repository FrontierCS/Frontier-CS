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
        # Calculate remaining work
        current_progress = sum(self.task_done_time)
        remaining_work = self.task_duration - current_progress

        # Check if task is already essentially done
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Retrieve environment parameters
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # --- Panic Mode Check ---
        # Determine if we are dangerously close to the deadline.
        # We calculate the minimum time required to finish:
        # 1. remaining_work: Actual compute time needed.
        # 2. overhead: Potential restart overhead if we switch to On-Demand or were paused.
        # 3. safety_buffer: Margin for the current step gap and general safety (2 steps).
        safety_buffer = 2.0 * gap
        required_time = remaining_work + overhead + safety_buffer

        if time_left < required_time:
            # Not enough slack to risk Spot interruptions or probing.
            # Use On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # --- Economy Mode ---
        # We have sufficient slack time. Prioritize cost minimization.
        if has_spot:
            # Spot is available in the current region. Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            # Since we have slack, we can spend time to find a region with Spot availability.
            # Switch to the next region (Round-Robin).
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # Return NONE (Pause) for this step.
            # Reasons:
            # 1. We cannot check 'has_spot' for the new region in the current step logic.
            # 2. Returning SPOT blindly is illegal if the new region lacks availability.
            # 3. Returning ON_DEMAND is expensive.
            # 4. Pausing costs $0 and consumes 'gap' time, which we can afford given the slack.
            # In the next step, 'has_spot' will reflect the new region's status.
            return ClusterType.NONE
