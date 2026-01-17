import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "optimal_scheduler"

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
        # Calculate progress and remaining constraints
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        remaining_time = self.deadline - self.env.elapsed_seconds

        # If task is already finished (should be handled by env, but safe to check)
        if remaining_work <= 0:
            return ClusterType.NONE

        # Panic Threshold Calculation
        # We must switch to On-Demand if the deadline is approaching and we can't risk
        # waiting for Spot availability or risking preemption.
        # Buffer includes:
        # 1. Restart overhead (time required to spin up a new instance)
        # 2. Safety margin (3 * gap_seconds) to handle time step granularity and decision lag
        safety_buffer = self.restart_overhead + (3.0 * self.env.gap_seconds)
        
        # If we are in the danger zone, prioritize completion over cost
        if remaining_time < (remaining_work + safety_buffer):
            return ClusterType.ON_DEMAND

        # If we have slack, prioritize cost
        if has_spot:
            return ClusterType.SPOT

        # If Spot is unavailable in the current region but we have plenty of time:
        # Switch to the next region to probe for Spot availability.
        # We return NONE for this step to avoid paying for On-Demand while searching.
        # In the next step, has_spot will reflect the new region's status.
        num_regions = self.env.get_num_regions()
        if num_regions > 1:
            next_region = (self.env.get_current_region() + 1) % num_regions
            self.env.switch_region(next_region)
        
        return ClusterType.NONE