import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostOptimizedStrategy"

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
        1. Calculate slack time (Time Left - Work Remaining - Overhead).
        2. If slack is low (Critical), force On-Demand to ensure deadline.
        3. If slack is high:
           - If Spot available: Use Spot (Cheapest).
           - If Spot unavailable: Switch Region and Wait (NONE).
             This avoids paying On-Demand prices while searching for Spot availability
             in other regions, leveraging the slack time.
        """
        # 1. Gather State
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # Precaution: if work is completed
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Calculate Slack
        # We need enough time to finish the work plus at least one restart overhead 
        # (in case we need to switch to OD).
        time_left = self.deadline - current_time
        time_needed_secure = work_remaining + self.restart_overhead
        slack = time_left - time_needed_secure
        
        # 3. Define Safety Buffer
        # We operate in discrete steps of 'gap_seconds'.
        # If we attempt to use Spot or Search, we might consume 'gap_seconds' without progress.
        # We need a buffer to safely switch to OD before it's too late.
        # 3.0 * gap ensures we have multiple steps of margin.
        safety_buffer = 3.0 * self.env.gap_seconds
        
        # 4. Critical Mode: Deadline approaching
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND
            
        # 5. Opportunity Mode: High Slack
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            # Since we have high slack, it is cheaper to switch regions and search
            # than to fall back to expensive On-Demand immediately.
            current_region_idx = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            
            # Switch to next region (Round-Robin)
            next_region_idx = (current_region_idx + 1) % num_regions
            self.env.switch_region(next_region_idx)
            
            # Return NONE for this step.
            # We cannot return SPOT because has_spot refers to the region at start of step.
            # We cannot guarantee availability in the new region until next step.
            # Using NONE costs $0.
            return ClusterType.NONE