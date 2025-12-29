import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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
        """
        Decide next action based on current state.
        """
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If task is practically completed
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_remaining = self.deadline - elapsed
        gap = self.env.gap_seconds
        
        # Determine overhead cost if we were to switch to OD right now.
        # If already OD, no new overhead to continue OD.
        # If SPOT or NONE, we would pay overhead to start OD.
        overhead_cost = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_cost = self.restart_overhead

        # Calculate safety buffer
        # We need:
        # 1. Time to do the work (work_remaining)
        # 2. Time for overhead (if we switch)
        # 3. Buffer for step granularity (we commit for 'gap')
        # 4. Extra margin for safety to avoid missing deadline
        # Buffer = 2 steps + margin relative to overhead
        safety_margin = 2.0 * gap + max(overhead_cost * 2, gap)
        
        # The threshold of remaining time below which we must run On-Demand to be safe
        panic_threshold = work_remaining + overhead_cost + safety_margin
        
        # Priority 1: Meet Deadline (Panic Mode)
        # If we are close to the point of no return, force On-Demand
        if time_remaining < panic_threshold:
            return ClusterType.ON_DEMAND

        # Priority 2: Use Spot if available
        if has_spot:
            # If we are currently ON_DEMAND, check if it's safe to switch back to SPOT
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Switching OD -> Spot incurs overhead and risk.
                # Only switch if we have substantial slack.
                # Threshold: panic_threshold + extra buffer (e.g., 4x overhead)
                switch_back_buffer = 4.0 * self.restart_overhead
                if time_remaining > panic_threshold + switch_back_buffer:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            # If not OD, definitely use Spot
            return ClusterType.SPOT

        # Priority 3: Spot unavailable in current region -> Search Strategy
        else:
            # If we are currently ON_DEMAND, we are safe but paying high cost.
            # Only search for Spot if we have very high slack to justify switching costs/risks.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Search implies: Switch Region (overhead reset) -> Wait Gap -> Try Spot
                # This wastes time. We need lots of slack.
                search_buffer = 10.0 * gap
                if time_remaining > panic_threshold + search_buffer:
                    # High slack, try to find Spot elsewhere
                    pass # Proceed to switch logic below
                else:
                    return ClusterType.ON_DEMAND

            # Switch Logic: Move to next region and wait
            # We assume round-robin search.
            
            # Check if we have enough time to search
            # Searching costs at least 1 gap (waiting in new region to check spot) + eventual overhead
            min_search_cost = 2.0 * gap + self.restart_overhead
            
            if time_remaining > panic_threshold + min_search_cost:
                current_region = self.env.get_current_region()
                num_regions = self.env.get_num_regions()
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
                # We switched region, so we must return NONE (or OD) for this step.
                # We return NONE to wait and check has_spot in the next step.
                return ClusterType.NONE
            else:
                # Not enough time to search, fallback to OD
                return ClusterType.ON_DEMAND