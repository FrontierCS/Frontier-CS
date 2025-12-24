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
        # Gather State
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        work_remaining = self.task_duration - done
        
        # If work is done, stop (though environment usually handles this)
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_left = self.deadline - elapsed
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Safety Logic:
        # We must finish before deadline.
        # Minimal time needed using On-Demand = work_remaining + restart_overhead.
        # If we delay decision by 1 step (return NONE or fail to find spot), we lose 'gap' seconds.
        # We enforce a safety buffer to switch to On-Demand if time is tight.
        # Buffer includes the current step gap (to be safe for next evaluation) plus overheads.
        safety_margin = work_remaining + overhead + (1.5 * gap) + overhead

        if time_left < safety_margin:
            # We are close to the deadline. Use On-Demand to guarantee completion.
            # Sticking to current region prevents unnecessary region-switch overheads 
            # if we were already here, though switching to OD forces overhead anyway if we weren't running.
            return ClusterType.ON_DEMAND

        # Cost Optimization Logic:
        if has_spot:
            # Spot is available and we have slack. Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region, but we have slack.
            # Strategy: Switch to the next region and wait (NONE) to probe its availability in the next step.
            # We iterate through regions in a cycle.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # We cannot return SPOT immediately because we don't know if the new region has spot.
            # Returning ON_DEMAND is expensive if we are just probing.
            # Returning NONE costs time (slack) but 0 money. Since we have slack, this is optimal.
            return ClusterType.NONE
