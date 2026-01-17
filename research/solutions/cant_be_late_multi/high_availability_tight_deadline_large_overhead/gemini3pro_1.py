import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "cant_be_late_strategy"

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
        # Calculate current progress and time constraints
        task_done = sum(self.task_done_time)
        work_left = self.task_duration - task_done
        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed

        # If task is done, stop
        if work_left <= 0:
            return ClusterType.NONE

        # Calculate the time required to finish if we use On-Demand (OD) immediately.
        # If we are not currently on OD, switching/starting incurs full restart overhead.
        # If we are already on OD, we only pay any remaining pending overhead.
        overhead_cost = 0.0
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_cost = self.remaining_restart_overhead
        else:
            overhead_cost = self.restart_overhead
            
        time_needed_od = work_left + overhead_cost

        # Determine safety buffer.
        # Decisions are made every gap_seconds.
        # We need to ensure that if we waste one step (e.g., waiting or searching),
        # we still have enough time to finish using OD.
        # A buffer of 2.0 * gap provides a safe margin.
        gap = self.env.gap_seconds
        safety_buffer = 2.0 * gap

        # Panic Logic: If time is tight, force On-Demand to guarantee deadline
        if time_left < (time_needed_od + safety_buffer):
            return ClusterType.ON_DEMAND

        # Economy Logic: Try to use Spot if available
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable in the current region.
            # Since we are not in panic mode, we can afford to search for Spot.
            # Switch to the next region and wait one step (NONE) to probe availability.
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                current_region = self.env.get_current_region()
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
            
            # Return NONE to avoid On-Demand costs while searching.
            # This consumes one time step (gap).
            return ClusterType.NONE