import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CantBeLateStrategy"

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
        
        # Initialize progress cache to avoid O(N^2) complexity with sum()
        self.cached_progress = 0.0
        self.last_step_count = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Efficiently calculate progress
        current_len = len(self.task_done_time)
        if current_len > self.last_step_count:
            self.cached_progress += sum(self.task_done_time[self.last_step_count:])
            self.last_step_count = current_len

        remaining_work = self.task_duration - self.cached_progress
        
        # If work is effectively done, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        # Determine if we are in a critical state
        # We need enough time to finish using On-Demand (efficiency 1.0)
        # plus overhead (if we need to restart/switch) plus a safety buffer.
        # Safety buffer of 1.5 gaps allows for one failed probe step + margin.
        overhead = self.restart_overhead
        safety_buffer = 1.5 * self.env.gap_seconds
        
        required_time = remaining_work + overhead + safety_buffer
        
        if remaining_time < required_time:
            # Critical: Slack is low. Use On-Demand to guarantee finish.
            return ClusterType.ON_DEMAND
        
        # If not critical, try to save money with Spot
        if has_spot:
            return ClusterType.SPOT
            
        # No Spot in current region, but we have slack.
        # Strategy: Switch to next region and probe (Wait).
        # We use ClusterType.NONE to avoid On-Demand costs while searching.
        # We cycle regions to ensure coverage.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        
        return ClusterType.NONE