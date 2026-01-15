import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostOptimizedStrategy"  # REQUIRED: unique identifier

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

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Retrieve current state
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        total_duration = self.task_duration
        needed = total_duration - done
        
        # Calculate time budget
        time_left = self.deadline - elapsed
        
        # Parameters
        gap = self.env.gap_seconds
        overhead_const = self.restart_overhead
        current_penalty = self.remaining_restart_overhead
        
        # Panic Threshold Calculation:
        # Determine if we must switch to On-Demand to guarantee completion.
        # We need enough time to finish work + clear any penalty + safety buffer.
        # Safety buffer accounts for the granularity of time steps (gap) and potential 
        # overheads if we make a switch. 
        # 3.0 * gap provides a robust buffer against losing a few steps to bad Spot attempts.
        safety_margin = (3.0 * gap) + (2.0 * overhead_const)
        
        if time_left < (needed + current_penalty + safety_margin):
            # Slack is critical; minimize risk by forcing On-Demand
            return ClusterType.ON_DEMAND
            
        # Cost Optimization Strategy
        if has_spot:
            # If Spot is available in current region, use it (cheapest option)
            return ClusterType.SPOT
        else:
            # Current region has no Spot, but we have sufficient slack.
            # Switch to the next region to search for Spot availability.
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # We return NONE to avoid paying On-Demand costs while moving/searching.
            # This consumes one time step (gap) but costs $0.
            return ClusterType.NONE