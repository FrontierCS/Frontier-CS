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
        """
        # Calculate amount of work completed and remaining
        done = sum(self.task_done_time)
        rem_work = self.task_duration - done
        
        # If task is finished, return NONE (though simulation usually stops)
        if rem_work <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate panic threshold.
        # We need 'rem_work' + 'overhead' (for potential restart) to finish using OD.
        # We add a safety buffer of 2.0 * gap (2 time steps) to handle simulation boundaries
        # and ensure we don't miss the deadline due to a last-minute preemption.
        panic_threshold = rem_work + overhead + (2.0 * gap)
        
        # If time is running out, force On-Demand to guarantee completion.
        if time_left < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # If we have slack, prioritize cost saving.
        if has_spot:
            return ClusterType.SPOT
        
        # If current region lacks Spot but we have slack:
        # Switch to the next region and pause (NONE) for one step.
        # In the next step, 'has_spot' will reflect the availability in the new region.
        num_regions = self.env.get_num_regions()
        curr_region = self.env.get_current_region()
        next_region = (curr_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        
        # Return NONE to incur no cost while moving/scanning
        return ClusterType.NONE