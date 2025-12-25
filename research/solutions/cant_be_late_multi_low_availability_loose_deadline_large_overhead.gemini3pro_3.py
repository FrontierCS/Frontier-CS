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
        # Retrieve state variables
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        
        # Calculate slack: Time available minus time strictly needed
        # We include restart_overhead in time_needed to account for potential restart costs
        time_remaining = self.deadline - elapsed
        time_needed = remaining_work + self.restart_overhead
        slack = time_remaining - time_needed
        
        gap = self.env.gap_seconds
        
        # Define safety threshold
        # If slack falls below this buffer, we must use On-Demand to guarantee completion.
        # 3.0 * gap provides a robust buffer against preemption loops near the deadline.
        PANIC_THRESHOLD = 3.0 * gap
        
        # 1. Critical Deadline Check
        if slack < PANIC_THRESHOLD:
            return ClusterType.ON_DEMAND
            
        # 2. Spot Availability Check
        if has_spot:
            # If current region has Spot and we have slack, use it (cheapest option)
            return ClusterType.SPOT
            
        # 3. Spot Hunting (Probing)
        # If Spot is unavailable in current region but we have plenty of slack:
        # Switch to the next region and wait 1 step (NONE) to check its availability.
        # This incurs a time penalty (gap_seconds) but no monetary cost.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        return ClusterType.NONE
