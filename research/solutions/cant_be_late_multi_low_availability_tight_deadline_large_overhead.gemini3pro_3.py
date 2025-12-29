import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cost-optimized multi-region scheduling strategy."""

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
        1. Calculate slack (time remaining - work needed).
        2. If slack is critical (< 2h), force On-Demand to guarantee completion.
        3. If Spot is available, use it.
        4. If Spot is unavailable and slack is high (> 5h), switch region and pause (NONE) to search for Spot cheaply.
        5. If Spot is unavailable and slack is medium, use On-Demand in current region to make progress.
        """
        # Constants
        GAP = self.env.gap_seconds
        OVERHEAD = self.restart_overhead
        
        # State calculations
        done = sum(self.task_done_time)
        total_needed = self.task_duration
        remaining_work = max(0.0, total_needed - done)
        
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_left = max(0.0, deadline - elapsed)
        
        # Calculate slack
        # We subtract overhead to be conservative (reserve time for at least one restart)
        slack = time_left - (remaining_work + OVERHEAD)
        
        # Thresholds
        # Critical: If we have less than 2 hours buffer, prioritize reliability
        CRITICAL_SLACK = 2.0 * GAP 
        # Search: If we have more than 5 hours buffer, search for Spot cheaply
        SEARCH_SLACK = 5.0 * GAP

        # 1. Critical Mode: Deadline approaching, strictly use reliable resources
        if slack < CRITICAL_SLACK:
            return ClusterType.ON_DEMAND

        # 2. Spot Available: Always prefer Spot if safe
        if has_spot:
            return ClusterType.SPOT

        # 3. Search Mode: Spot unavailable in current region
        num_regions = self.env.get_num_regions()
        if num_regions > 1:
            if slack > SEARCH_SLACK:
                # We have plenty of time. Switch to next region and pause (NONE).
                # This incurs no monetary cost but consumes time (1 step).
                # Next step we will check if this new region has Spot.
                next_region = (self.env.get_current_region() + 1) % num_regions
                self.env.switch_region(next_region)
                return ClusterType.NONE
        
        # 4. Fallback Mode: Medium slack or single region
        # We can't afford to waste time searching (NONE), but we shouldn't switch regions blindly 
        # using OD because that incurs overhead repeatedly.
        # Best strategy is to stay in current region and use OD to ensure progress.
        return ClusterType.ON_DEMAND