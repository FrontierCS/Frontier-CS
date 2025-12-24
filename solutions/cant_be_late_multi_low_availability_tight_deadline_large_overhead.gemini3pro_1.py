import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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
        # 1. Gather State
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        done_time = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - done_time)
        time_elapsed = self.env.elapsed_seconds
        time_until_deadline = self.deadline - time_elapsed
        
        # 2. Determine Strategy Mode
        # Calculate minimum time needed to finish safely on On-Demand
        # We add a safety buffer to account for timestep granularity (gap_seconds) and overhead risks.
        # Buffer of 2 hours (7200s) is safe given typical 1h gaps and 12h slack.
        safety_buffer = 7200.0
        min_safe_time = work_remaining + self.restart_overhead + safety_buffer

        # Mode A: Panic / Safety First
        # If we are close to the point of no return, switch to On-Demand immediately.
        # We accept the cost to ensure we don't miss the deadline penalty.
        if time_until_deadline < min_safe_time:
            return ClusterType.ON_DEMAND

        # Mode B: Economy
        # If we have slack, prioritize cost savings.
        
        if has_spot:
            # If Spot is available in current region, use it.
            return ClusterType.SPOT
        else:
            # If Spot is unavailable here, but we have slack:
            # Switch to the next region and pause (NONE) for this step.
            # This "hunting" strategy explores regions for Spot availability 
            # at the cost of elapsed time (slack) rather than money.
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            return ClusterType.NONE
