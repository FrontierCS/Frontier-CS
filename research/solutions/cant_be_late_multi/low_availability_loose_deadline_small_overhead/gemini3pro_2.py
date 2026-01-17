import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cost_optimized_strategy"

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
        done_seconds = sum(self.task_done_time)
        needed_seconds = self.task_duration - done_seconds

        if needed_seconds <= 0:
            return ClusterType.NONE

        # Calculate time constraints
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        # Calculate effective available time.
        # We subtract remaining_restart_overhead because if we start running now,
        # that time is consumed before progress begins.
        effective_time = remaining_time - self.remaining_restart_overhead
        
        # Slack is the buffer we have before we MUST run perfectly to finish.
        slack = effective_time - needed_seconds

        # Determine threshold for panic mode (switching to On-Demand).
        # We maintain a safety buffer of 3 * gap_seconds.
        # This protects against:
        # 1. Step quantization (gap_seconds)
        # 2. Potential preemption overhead near the deadline
        # 3. Switching overhead
        panic_threshold = 3.0 * self.env.gap_seconds

        if slack < panic_threshold:
            # Urgency is high: prioritize deadline over cost
            return ClusterType.ON_DEMAND

        # If not urgent, prioritize cost
        if has_spot:
            return ClusterType.SPOT
        
        # Spot is not available in current region, but we have slack.
        # Strategy: Hunt for Spot in other regions.
        if self.env.get_num_regions() > 1:
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % self.env.get_num_regions()
            self.env.switch_region(next_region)
            
        # Return NONE to avoid paying On-Demand cost while searching or waiting.
        # This consumes time (reducing slack) but saves money.
        return ClusterType.NONE