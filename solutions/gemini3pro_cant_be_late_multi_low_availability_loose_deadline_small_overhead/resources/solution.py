import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_strategy"

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
        # 1. Calculate progress and remaining work
        elapsed = self.env.elapsed_seconds
        current_done = sum(self.task_done_time)
        remaining_work = self.task_duration - current_done

        # If task is effectively done, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        time_left = self.deadline - elapsed
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        num_regions = self.env.get_num_regions()

        # 2. Determine Panic Threshold
        # We must switch to On-Demand (Guaranteed) if we are running out of slack.
        # We need time for:
        # - The remaining work itself
        # - Restart overhead (if we switch to OD)
        # - A safety buffer to account for:
        #   a) Probing other regions (wasting 'gap' seconds per switch)
        #   b) Discrete timestep quantization
        # Buffer = (Time to probe all regions) + (1 extra step margin)
        safety_buffer = (num_regions * gap) + gap + overhead

        # If remaining time is critically low, force On-Demand
        if time_left < (remaining_work + overhead + safety_buffer):
            return ClusterType.ON_DEMAND

        # 3. Spot Instance Strategy
        if has_spot:
            # Spot is available in current region, use it
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            # Strategy: Switch to next region and wait (NONE) for one step to safely probe.
            # We don't return SPOT immediately to avoid violating the has_spot constraint
            # if the new region also lacks availability.
            if num_regions > 1:
                curr_region = self.env.get_current_region()
                next_region = (curr_region + 1) % num_regions
                self.env.switch_region(next_region)
            
            # Return NONE to pay the time cost of switching/probing without risking a crash
            return ClusterType.NONE
