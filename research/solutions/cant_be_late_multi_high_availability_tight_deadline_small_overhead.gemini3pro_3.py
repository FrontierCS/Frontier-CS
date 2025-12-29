import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

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
        
        Strategy:
        1. Calculate 'Slack': Time remaining minus work remaining.
        2. Panic Mode: If slack is low (close to deadline), force ON_DEMAND to ensure completion.
        3. Cost Optimization: If slack is sufficient:
           - If Spot available in current region -> Use SPOT.
           - If Spot unavailable -> Switch to next region and wait (NONE) to probe there next step.
        """
        # 1. State Calculation
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        # If task is effectively done, return NONE
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # 2. Panic Mode Check
        # Calculate overhead we would pay if we switched to OD now (0 if already on OD)
        switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead
        
        # Safety buffer: 
        # We need to guarantee we can finish. 
        # We use a buffer of 2.5 * gap to account for:
        # - The current step duration
        # - Discrete step granularity 
        # - Safety margin against exact deadline failures
        safety_buffer = 2.5 * gap
        
        min_required_time = work_remaining + switch_overhead
        
        # If we are dangerously close to running out of time, use reliable On-Demand
        if time_left < min_required_time + safety_buffer:
            return ClusterType.ON_DEMAND

        # 3. Cost Optimization (Safe to explore)
        if has_spot:
            # Cheapest option available
            return ClusterType.SPOT
        else:
            # Spot not available here. We have enough slack to "hunt" for spot elsewhere.
            # We switch region and return NONE. 
            # This costs us 1 time step (gap) of idling but saves money if we find Spot.
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE