import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "solution_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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
        1. Always prefer SPOT if available in the current region (cheapest).
        2. If SPOT is not available:
           - Check if we have enough slack to "search" for SPOT in other regions.
           - Searching involves switching region and waiting one step (ClusterType.NONE).
           - If slack is tight (critical), switch to ON_DEMAND to guarantee completion.
        """
        # 1. Update state metrics
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If work is effectively done, do nothing
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # 2. Determine Urgency
        # If we wait one step (gap_seconds) to search/travel, will we still meet the deadline?
        # We calculate the remaining time *after* the wait.
        # We must accommodate the work remaining PLUS potential restart overhead.
        # We add a safety buffer (2 * overhead) to be robust.
        
        future_time_available = time_remaining - gap
        time_required = work_remaining + overhead
        safety_buffer = 2.0 * overhead
        
        can_afford_search = (future_time_available - safety_buffer) > time_required

        # 3. Decision Logic
        if has_spot:
            # Optimal case: Spot is available. Use it.
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            if can_afford_search:
                # We have time to look for a better region.
                # Switch to the next region (Round-Robin) and wait this step.
                current_idx = self.env.get_current_region()
                num_regions = self.env.get_num_regions()
                next_region = (current_idx + 1) % num_regions
                
                self.env.switch_region(next_region)
                
                # Return NONE: "pause" execution to save cost while moving/searching
                return ClusterType.NONE
            else:
                # Critical state: Not enough time to search. Must work now.
                # Use On-Demand which is guaranteed available.
                return ClusterType.ON_DEMAND
