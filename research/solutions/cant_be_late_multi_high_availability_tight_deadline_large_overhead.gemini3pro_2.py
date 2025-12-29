import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Strategy that maintains slack awareness and scans regions for spot availability."""

    NAME = "slack_scanner"

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
        Decide next action based on slack time and spot availability.
        """
        # Gather current state
        elapsed = self.env.elapsed_seconds
        done_work = sum(self.task_done_time)
        work_remaining = self.task_duration - done_work
        
        # Edge case: Task completed
        if work_remaining <= 0:
            return ClusterType.NONE

        current_overhead = self.remaining_restart_overhead
        time_remaining = self.deadline - elapsed
        
        # Calculate Slack: Time remaining minus minimum time required to finish
        # Minimum time = Remaining Work + Current Pending Overhead
        slack = time_remaining - (work_remaining + current_overhead)
        
        # Safety Buffer:
        # We switch to On-Demand if slack falls below a safe threshold.
        # Restart overhead is typically 0.2h (720s). 
        # A buffer of 3600s (1 hour) allows for multiple restart attempts or 
        # region scanning steps without breaching the deadline.
        SAFE_BUFFER = 3600.0

        # 1. Critical Phase: Low slack -> Use On-Demand to guarantee deadline
        if slack < SAFE_BUFFER:
            return ClusterType.ON_DEMAND

        # 2. Economical Phase: High slack -> Prefer Spot
        if has_spot:
            return ClusterType.SPOT
        
        # 3. Search Phase: Spot unavailable -> Switch Region
        # We switch to the next region and return NONE.
        # This incurs no monetary cost and advances time by one step.
        # In the next step, `has_spot` will reflect the new region's status.
        # Switching regions forces a restart overhead on the next launch, 
        # but overheads do not stack, so we only pay it once when we finally pick a region.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        
        return ClusterType.NONE