import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "optimal_strategy"

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
        # Calculate state
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        time_left = self.deadline - elapsed
        
        # Panic Threshold Calculation
        # We need to ensure we have enough time to finish using On-Demand instances.
        # Time required = remaining work + overhead (for switching/starting)
        # We add a safety buffer to account for step granularity and safety factor.
        # A 1-hour buffer (3600s) is safe given the 12-hour slack in the problem setting.
        buffer = max(3600.0, self.restart_overhead * 5.0)
        
        # Check if we are approaching the deadline
        if time_left < (remaining_work + self.restart_overhead + buffer):
            # Panic mode: Switch to On-Demand to guarantee completion
            return ClusterType.ON_DEMAND
        
        # If we have slack, prioritize Cost (Spot instances)
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            # Instead of waiting or paying for On-Demand, we switch regions to find Spot availability.
            # This "scanning" incurs overhead but is optimal given the long duration of spot outages.
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            self.env.switch_region(next_region)
            return ClusterType.NONE
