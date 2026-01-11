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

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Calculate progress
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        gap = self.env.gap_seconds
        
        # Panic Logic:
        # Determine if we must switch to On-Demand to guarantee meeting the deadline.
        # If we switch to OD, we incur restart_overhead (unless already on OD).
        overhead_cost = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_cost = self.restart_overhead
            
        time_needed_od = remaining_work + overhead_cost
        
        # We need a safety buffer. If we attempt Spot or switch regions this step,
        # we risk consuming 'gap' seconds without progress.
        # We must ensure that even if this step yields 0 progress, we can still finish with OD.
        # Condition: remaining_time - gap >= time_needed_od
        # We add an extra 0.5 * gap buffer for safety.
        safety_threshold = time_needed_od + (1.5 * gap)
        
        if remaining_time < safety_threshold:
            return ClusterType.ON_DEMAND

        # Strategy Logic:
        # If we have slack, prioritize Spot instances to save cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            # No Spot capacity in current region.
            # Since we have slack, switch to the next region to search for capacity.
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            # Return NONE to allow the switch to take effect and check availability in next step
            return ClusterType.NONE