import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "robust_cost_optimizer"

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
        1. Calculate remaining work and remaining time.
        2. If time is running out (critical slack), force On-Demand to guarantee completion.
        3. If there is slack:
           - Use Spot if available in current region.
           - If Spot unavailable, switch to next region and wait (NONE) to probe availability.
        """
        # Gather state
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        time_left = self.deadline - elapsed
        
        # Check if task is complete
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Parameters
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate Safety Threshold
        # We need time for: Remaining Work + Potential Overhead + Timestep Alignment Buffer
        # If time_left drops below this, we cannot risk searching or preemption.
        safety_buffer = overhead + (2.0 * gap)
        
        if time_left < (remaining_work + safety_buffer):
            # Critical zone: Force On-Demand for reliability
            return ClusterType.ON_DEMAND

        # If not critical, optimize for cost
        if has_spot:
            # Spot is available here, use it
            return ClusterType.SPOT
        else:
            # Spot unavailable here, and we have slack.
            # Switch region to find Spot.
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # Return NONE because we don't know if the new region has Spot yet.
            # We must wait for next step to check 'has_spot' for the new region.
            return ClusterType.NONE