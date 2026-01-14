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
        # Calculate remaining work and time
        done_time = sum(self.task_done_time)
        work_remaining = self.task_duration - done_time
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Determine safety buffer
        # We need a buffer to safely switch to On-Demand if Spot availability is consistently bad.
        # Use max of 2 hours or 2 timesteps to be robust against large gaps.
        gap = self.env.gap_seconds
        safety_buffer = max(2.0 * 3600, 2.0 * gap)
        
        # Calculate critical time threshold
        # Time required = Work Remaining + Restart Overhead (in case of switch) + Safety Buffer
        critical_threshold = work_remaining + self.restart_overhead + safety_buffer
        
        # Check if we are in "Panic Mode"
        # If time is running out, force On-Demand execution to ensure deadline is met.
        if time_remaining < critical_threshold:
            return ClusterType.ON_DEMAND
            
        # If not critical, prefer Spot instances to minimize cost
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable in the current region.
            # Strategy: Switch to the next region and wait (ClusterType.NONE) for this step.
            # Returning NONE incurs no cost (besides time) and allows the restart overhead 
            # to be processed. In the next step, we will check has_spot for the new region.
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            self.env.switch_region(next_region)
            return ClusterType.NONE