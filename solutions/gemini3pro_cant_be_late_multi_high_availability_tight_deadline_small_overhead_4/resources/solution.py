import json
import random
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "cant_be_late_strategy"

    def solve(self, spec_path: str) -> "Solution":
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
        # State variables
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_needed = self.task_duration - work_done
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # If finished, stop
        if work_needed <= 0:
            return ClusterType.NONE

        time_remaining = self.deadline - elapsed
        
        # Calculate time required if we switched to OD right now
        # We conservatively assume we might need a restart (overhead)
        time_required_od = work_needed + overhead
        
        # Define Safety Buffer
        # We use a dynamic buffer based on remaining work and gap size
        # 10% of remaining work or 2 gaps, whichever is larger, to be safe against variance
        safety_buffer = max(work_needed * 0.1, 2.0 * gap)
        
        # Panic Condition: Check if we have enough slack
        # Slack = Time Available - Time Needed
        # If Slack < Cost of searching (Gap) + Buffer, we panic
        slack = time_remaining - time_required_od
        is_panic = slack < (gap + safety_buffer)

        # Decision Logic
        if is_panic:
            # We are close to deadline. Prioritize completion over cost.
            # ON_DEMAND is guaranteed and avoids further search penalties.
            return ClusterType.ON_DEMAND
        
        if has_spot:
            # Spot is available and we have slack. Use it to save money.
            return ClusterType.SPOT
        else:
            # Spot unavailable, but we have slack.
            # Strategy: Switch region to try and find Spot availability.
            # We use a simple round-robin approach to cycle through regions.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # We return NONE to probe the new region in the next step.
            # We cannot return SPOT immediately because we don't know the new region's status,
            # and returning SPOT when unavailable raises an error.
            return ClusterType.NONE
