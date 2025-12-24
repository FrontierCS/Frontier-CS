import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "AdaptiveCostOptimizer"

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
        Prioritize finishing before deadline, then minimizing cost.
        """
        # Calculate work remaining and time left
        done_time = sum(self.task_done_time)
        remaining_work = self.task_duration - done_time
        elapsed_time = self.env.elapsed_seconds
        time_left = self.deadline - elapsed_time

        # Calculate the safety threshold to switch to On-Demand.
        # We need enough time to finish the work plus the restart overhead.
        # We add a buffer of 1.5 * gap_seconds to handle step granularity and safety margin.
        safety_buffer = self.env.gap_seconds * 1.5
        required_time = remaining_work + self.restart_overhead + safety_buffer

        # Panic Logic: If we are cutting it close, strictly use On-Demand.
        # This guarantees completion if physically possible within the remaining time.
        if time_left < required_time:
            return ClusterType.ON_DEMAND

        # Cost Logic: If we have slack, prioritize Spot.
        if has_spot:
            return ClusterType.SPOT
        
        # Spot Unavailable Logic:
        # If Spot is not available in the current region and we are not panicking,
        # we switch to another region to search for availability.
        num_regions = self.env.get_num_regions()
        if num_regions > 1:
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
        
        # Return NONE for this step to allow the environment to switch/probe.
        # We cannot return SPOT immediately after switching as we don't know availability yet.
        # We avoid ON_DEMAND here to save costs, spending our slack time to find cheap Spot.
        return ClusterType.NONE
