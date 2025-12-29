import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cost-aware multi-region scheduling strategy."""

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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        Prioritize Spot instances when slack permits.
        Switch regions to find Spot availability if unavailable.
        Force On-Demand when close to deadline.
        """
        # Gather state
        elapsed = self.env.elapsed_seconds
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        remaining_time = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # If task is logically complete, stop (though env usually handles this)
        if remaining_work <= 0:
            return ClusterType.NONE

        # Safety buffer calculation
        # We need to guarantee completion on On-Demand even if we incur a restart overhead immediately.
        # We add 2 * gap_seconds as a safety margin to account for step quantization and decision boundaries.
        # If remaining_time falls below this threshold, we enter "Critical Mode".
        safety_threshold = remaining_work + overhead + (2.0 * gap)

        if remaining_time < safety_threshold:
            # Critical Mode: Not enough slack to risk Spot preemption or searching.
            # Use On-Demand to guarantee completion before deadline.
            # We do not switch regions here to avoid unnecessary overhead delay.
            return ClusterType.ON_DEMAND

        # Economy Mode: We have sufficient slack to prefer Spot instances.
        if has_spot:
            # Spot is available in the current region. Use it.
            return ClusterType.SPOT
        else:
            # Spot is not available in the current region.
            # Strategy: Switch to the next region and pause (NONE) for one step.
            # This "polls" the next region for Spot availability without incurring On-Demand costs.
            # Since we have slack, trading time (one step) for potential cost savings is optimal.
            
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            
            # Round-robin region switching
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            return ClusterType.NONE