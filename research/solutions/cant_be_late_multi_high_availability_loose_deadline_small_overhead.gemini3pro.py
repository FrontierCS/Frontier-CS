import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostOptimizedStrategy"

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
        Prioritizes finishing the task before deadline, then minimizing cost by using Spot instances.
        """
        # Calculate current state metrics
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - work_done)
        time_remaining = max(0.0, self.deadline - elapsed)
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate safety threshold
        # We must switch to On-Demand if the remaining time is close to the work required.
        # We add a buffer of (3 * gap) to account for time step granularity and any transition delays.
        # We add (2 * overhead) to cover restart costs if we are currently stopped or need to switch.
        safety_threshold = work_remaining + (3.0 * gap) + (2.0 * overhead)
        
        # 1. Safety Fallback: If close to deadline, force On-Demand to avoid penalty.
        if time_remaining <= safety_threshold:
            return ClusterType.ON_DEMAND

        # 2. Spot Usage: If we have slack and Spot is available, use it (cheapest option).
        if has_spot:
            return ClusterType.SPOT

        # 3. Exploration: If current region lacks Spot but we have plenty of slack.
        # Switch to the next region in round-robin order to check for Spot availability.
        # We return NONE (pause) for this step because we cannot guarantee Spot availability 
        # in the new region immediately, and returning SPOT blindly is prohibited.
        # This incurs a time cost of 'gap' seconds, which is acceptable given the slack.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        return ClusterType.NONE