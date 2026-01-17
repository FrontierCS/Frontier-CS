import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cost_optimized_strategy"

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
        1. Calculate Slack: (Time Remaining) - (Work Remaining + Overhead).
        2. Panic Mode: If Slack < 4 hours, force ClusterType.ON_DEMAND to ensure deadline is met.
        3. Hunt Mode: If Slack is high:
           - If Spot available: Use ClusterType.SPOT.
           - If Spot unavailable: Switch region and return ClusterType.NONE (wait) to find a better region.
        """
        # Calculate state metrics
        done_seconds = sum(self.task_done_time)
        remaining_work_seconds = self.task_duration - done_seconds
        elapsed_seconds = self.env.elapsed_seconds
        remaining_time_seconds = self.deadline - elapsed_seconds
        
        # Calculate slack
        # We subtract one restart overhead to conservatively estimate time needed to finish
        current_slack = remaining_time_seconds - (remaining_work_seconds + self.restart_overhead)
        
        # Define Panic Threshold (4 hours)
        # If we are close to the wire, we stop optimizing for cost and ensure completion.
        PANIC_THRESHOLD_SECONDS = 4.0 * 3600
        
        if current_slack < PANIC_THRESHOLD_SECONDS:
            # Panic Mode: Force On-Demand to guarantee completion.
            # We stick to the current region to avoid further switch overheads/delays.
            return ClusterType.ON_DEMAND
            
        # Normal Mode: Optimize for Cost
        if has_spot:
            # If Spot is available in the current region, use it (cheapest option).
            return ClusterType.SPOT
        else:
            # Spot not available in current region.
            # Strategy: Switch to the next region and wait one step.
            # We return NONE to avoid paying On-Demand costs while "searching".
            # By returning NONE, we effectively spend time to find a cheaper resource.
            # Since slack is high, this trade-off (Time for Cost) is favorable.
            
            num_regions = self.env.get_num_regions()
            current_idx = self.env.get_current_region()
            next_idx = (current_idx + 1) % num_regions
            
            self.env.switch_region(next_idx)
            
            return ClusterType.NONE