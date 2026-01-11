import json
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
        # Calculate remaining work and time
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        time_left = self.deadline - self.env.elapsed_seconds

        # Safety threshold calculation
        # We must switch to On-Demand if we are close to the deadline.
        # We need enough time to:
        # 1. Pay the restart overhead (if any)
        # 2. Complete the remaining work
        # 3. Absorb a buffer for the discrete time steps (gap_seconds)
        # Using 2.1 * gap_seconds provides a robust safety margin to prevent 
        # missing the deadline due to step granularity or one failed attempt.
        safety_margin = self.restart_overhead + (2.1 * self.env.gap_seconds)
        
        # Panic condition: If we are close to the deadline, force On-Demand.
        if time_left < (remaining_work + safety_margin):
            return ClusterType.ON_DEMAND

        # Normal operation: Prefer Spot instances to minimize cost
        if has_spot:
            return ClusterType.SPOT
        else:
            # If Spot is not available in the current region, switch to the next one.
            # We cycle through regions in a round-robin fashion to find availability.
            # We return NONE for this step because we cannot immediately use Spot 
            # in the new region without verifying availability in the next step.
            current_region_idx = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region_idx = (current_region_idx + 1) % num_regions
            
            self.env.switch_region(next_region_idx)
            return ClusterType.NONE