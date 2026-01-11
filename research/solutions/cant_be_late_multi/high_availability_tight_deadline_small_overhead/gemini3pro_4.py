import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cost-optimized strategy that searches for Spot instances across regions."""

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
        Strategy:
        1. Calculate slack (time remaining - work remaining).
        2. If slack is critically low (Panic Mode), force ON_DEMAND to guarantee completion.
        3. If slack is sufficient:
           - If Spot is available, use SPOT.
           - If Spot is unavailable, switch region and wait (NONE) to preserve cost while searching.
        """
        # Current state parameters
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_region_idx = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Work tracking
        done = sum(self.task_done_time)
        needed = self.task_duration - done
        time_left = self.deadline - elapsed
        
        # Slack: How much time buffer we have
        slack = time_left - needed

        # Define Panic Threshold
        # If slack < threshold, we risk missing deadline due to overheads or further unavailability.
        # We assume 2 gaps + overhead is a safe buffer to absorb transition costs.
        # If gap is 1 hour, this gives us ~2 hours of buffer before we force OD.
        panic_threshold = 2.0 * gap + self.restart_overhead

        # Decision Logic
        if slack < panic_threshold:
            # Panic Mode: Not enough slack to search or risk Spot interruptions.
            # Use On-Demand to ensure we meet the deadline.
            return ClusterType.ON_DEMAND
        
        if has_spot:
            # Safe Mode & Spot Available: Use Spot to minimize cost.
            return ClusterType.SPOT
        else:
            # Safe Mode & Spot Unavailable:
            # We have enough slack to "shop around" for a region with Spot availability.
            # Switch to the next region (round-robin) and pause execution (NONE)
            # to avoid paying On-Demand prices while searching.
            next_region = (current_region_idx + 1) % num_regions
            self.env.switch_region(next_region)
            return ClusterType.NONE