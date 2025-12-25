import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cost-aware multi-region scheduling strategy."""

    NAME = "CostAwareSlackStrategy"

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
        Prioritizes Spot instances to minimize cost.
        Switches regions if Spot is unavailable and slack permits.
        Falls back to On-Demand if deadline is approaching.
        """
        # 1. Update State
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If finished (should be handled by env, but safe to check)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        time_left = self.deadline - current_time
        
        # 2. Calculate Slack and Thresholds
        # Slack is the time buffer we have relative to the work needed.
        # We subtract overhead to account for the restart cost of switching to OD/starting.
        slack = time_left - remaining_work - self.restart_overhead
        
        # Define a safety buffer. If slack falls below this, we panic.
        # The buffer must cover the current time step (gap) because we make decisions for the interval.
        # We also add extra padding to account for overheads and safety.
        # 2 * gap + 2 * overhead is a heuristic to ensure we don't miss the deadline due to discretization.
        buffer_seconds = 2.0 * self.env.gap_seconds + 2.0 * self.restart_overhead
        
        # Enforce a minimum absolute buffer (e.g., 30 mins) to handle noise or small gaps
        min_buffer = 1800.0 
        safety_threshold = max(buffer_seconds, min_buffer)

        # 3. Decision Logic
        
        # CRITICAL CASE: Low slack -> Force On-Demand
        if slack < safety_threshold:
            return ClusterType.ON_DEMAND

        # NORMAL CASE: High slack -> Prefer Spot
        if has_spot:
            # Spot is available in current region. Use it.
            # Even if we were previously on OD, switching to Spot is worth it due to cost diff.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            # Strategy: Search for Spot in other regions.
            # Since we have high slack, it is cheaper to Wait/Search than to run OD.
            
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                # Switch to the next region in a round-robin fashion
                current_region_idx = self.env.get_current_region()
                next_region_idx = (current_region_idx + 1) % num_regions
                self.env.switch_region(next_region_idx)
            
            # We cannot use Spot immediately after switching (we don't know if the new region has spot yet).
            # We return NONE to pause execution for this step. The next step will see the updated region context.
            return ClusterType.NONE
