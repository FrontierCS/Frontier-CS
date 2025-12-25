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
        # Calculate remaining work
        remaining_work = self.task_duration - sum(self.task_done_time)
        
        # If task is essentially done, return NONE (sim should end)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Current status
        current_time = self.env.elapsed_seconds
        time_until_deadline = self.deadline - current_time
        
        # Calculate overhead cost if we use On-Demand
        # If we are already on OD, overhead is 0 (continuing).
        # If we are on Spot or None, we incur restart_overhead to start OD.
        overhead_penalty = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_penalty = self.restart_overhead

        # Time required to finish using purely On-Demand
        time_needed_od = remaining_work + overhead_penalty
        
        # Safety Buffer:
        # We need to ensure we switch to OD before it's mathematically impossible to finish.
        # We add a buffer of 2 time steps (gaps) to account for discrete time steps,
        # potential overhead alignment, and safety against floating point issues.
        buffer = 2.0 * self.env.gap_seconds
        
        # DEADLINE GUARD:
        # If slack is exhausted, force On-Demand to guarantee completion.
        if time_until_deadline <= (time_needed_od + buffer):
            return ClusterType.ON_DEMAND

        # COST OPTIMIZATION:
        # If we have slack, prioritize Spot (cheaper).
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            # Strategy: Switch to the next region and wait 1 step.
            # We cycle through regions (Round-Robin) to find available Spot.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # We must return NONE (or OD) because we don't know the Spot status 
            # of the new region until the next timestep. 
            # Using SPOT blindly would error if unavailable.
            return ClusterType.NONE
