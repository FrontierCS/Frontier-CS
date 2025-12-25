import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Adaptive multi-region scheduling strategy."""

    NAME = "CostMinimizerStrategy"

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
        1. Calculate safety margin. If we are close to the deadline (Panic Mode),
           force use of On-Demand instances to guarantee completion.
        2. If strictly safe, prefer Spot instances (cheaper).
        3. If Spot is unavailable in the current region, switch to the next region
           and wait (NONE) for the next timestep to check availability, rather than
           paying for On-Demand immediately.
        """
        # Retrieve current state
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - work_done)
        time_remaining = self.deadline - elapsed
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate panic threshold
        # We need enough time to finish the work plus restart overhead.
        # We add a buffer of ~1.5 gaps to account for discrete time steps and potential 
        # inefficiencies/interruptions right before the switch.
        # If time remaining drops below this, we risk missing the deadline.
        panic_threshold = work_remaining + 3.0 * overhead + 1.5 * gap
        
        if time_remaining < panic_threshold:
            # Panic mode: Deadline approaching.
            # Use On-Demand to ensure completion. Even if we have overhead pending,
            # On-Demand is reliable.
            return ClusterType.ON_DEMAND

        # Normal mode: We have slack. Prioritize cost savings.
        if has_spot:
            # Spot is available in current region. Use it.
            return ClusterType.SPOT
        
        # Spot is unavailable in current region, but we have enough slack (not in panic mode).
        # Instead of paying for OD, we explore other regions.
        # Switch to the next region (Round Robin).
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        
        # Return NONE for this step. We lose 'gap' seconds of time, but we save money.
        # In the next step, has_spot will reflect the new region's availability.
        return ClusterType.NONE
