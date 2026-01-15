import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_strategy"

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
        # Gather state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If task is complete
        if work_remaining <= 0:
            return ClusterType.NONE

        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        time_remaining = deadline - elapsed

        # Safety buffer: 3 time steps + overhead. 
        # Ensures we switch to OD with enough time to finish even if we just incurred overhead.
        safety_buffer = 3.0 * gap
        min_time_needed_od = work_remaining + overhead + safety_buffer

        # Panic check: If time is tight, force On-Demand to ensure completion
        if time_remaining < min_time_needed_od:
            return ClusterType.ON_DEMAND

        # Cost optimization strategy:
        # Prefer Spot instances. If Spot is unavailable in current region,
        # switch to next region and search (return NONE while switching).
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot unavailable here, move to next region
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # Return NONE because we cannot use SPOT in the current step 
            # (has_spot was False for the region we started in)
            return ClusterType.NONE