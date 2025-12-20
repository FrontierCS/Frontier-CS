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
        # Strategy Thresholds
        # If slack < 2.0 hours, stop optimizing for cost and ensure completion
        PANIC_SLACK_HOURS = 2.0
        # If slack > 6.0 hours, we can afford to wait (NONE) while switching regions to find Spot
        SEEK_SLACK_HOURS = 6.0

        # Gather State
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_needed = self.task_duration - work_done
        if work_needed < 0:
            work_needed = 0.0

        # Pending overhead
        current_overhead = self.remaining_restart_overhead if self.remaining_restart_overhead is not None else 0.0

        # Calculate Slack
        # Slack = Time Remaining - (Work Needed + Pending Overhead)
        time_left = self.deadline - current_time
        slack_seconds = time_left - (work_needed + current_overhead)
        slack_hours = slack_seconds / 3600.0

        # 1. Safety Check: Low Slack
        if slack_hours < PANIC_SLACK_HOURS:
            # Force On-Demand to guarantee progress. 
            # We stay in the current region to avoid incurring unnecessary switch overheads 
            # unless we were already switching, but OD is safe everywhere.
            return ClusterType.ON_DEMAND

        # 2. Prefer Spot
        if has_spot:
            return ClusterType.SPOT

        # 3. Spot Unavailable: Hunt for Spot
        # Switch to the next region in a round-robin fashion
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)

        # 4. Action during Search
        # If we have plenty of slack, return NONE to save money (paying only time)
        # If slack is tightening, use ON_DEMAND to progress task while moving
        if slack_hours > SEEK_SLACK_HOURS:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
