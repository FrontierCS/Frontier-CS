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

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead
        """
        # 1. Calculate current state
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - work_done)
        time_elapsed = self.env.elapsed_seconds
        time_remaining = max(0.0, self.deadline - time_elapsed)

        # 2. Determine threshold for forcing On-Demand (OD)
        # We calculate the time required to finish if we switch to OD right now.
        
        # If we are not currently on OD, switching incurs the full restart overhead.
        # If we are already on OD, we only need to account for any currently pending overhead.
        od_overhead_cost = 0.0
        if last_cluster_type == ClusterType.ON_DEMAND:
            od_overhead_cost = self.remaining_restart_overhead
        else:
            od_overhead_cost = self.restart_overhead

        time_needed_on_od = work_remaining + od_overhead_cost
        
        # Define a safety buffer.
        # This accounts for the granularity of the time steps (env.gap_seconds) and
        # provides a margin of safety against unexpected delays.
        # Assuming gap_seconds is around 3600 (1 hour), a 2-hour buffer is robust.
        buffer = 7200.0

        # 3. Critical Check: Force OD if slack is low
        if time_remaining < time_needed_on_od + buffer:
            return ClusterType.ON_DEMAND

        # 4. Spot Strategy: Minimize cost
        if has_spot:
            # If Spot is available in current region, use it.
            return ClusterType.SPOT
        else:
            # If Spot is unavailable in current region, we should move.
            # Strategy: Switch to the next region and wait (NONE) one step.
            # We wait because we cannot verify Spot availability in the new region 
            # until the next time step.
            
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            return ClusterType.NONE
