import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostMinimizingSlackStrategy"

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
        # Calculate current progress and time constraints
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate Panic Threshold
        # We must switch to On-Demand if the remaining time is critically low.
        # Critical time = Time needed to finish work + Restart overhead (in case we need to switch/start)
        # We add a safety buffer of 2.0 * gap_seconds to handle step quantization and boundary conditions.
        safety_buffer = 2.0 * gap
        panic_threshold = remaining_work + overhead + safety_buffer
        
        # Strategy Priority 1: Guarantee Deadline
        # If slack is exhausted, force On-Demand usage to ensure completion.
        if time_left < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # Strategy Priority 2: Minimize Cost using Spot
        # If we have slack and Spot is available in the current region, use it.
        if has_spot:
            return ClusterType.SPOT
            
        # Strategy Priority 3: Search for Spot
        # If Spot is unavailable in current region and we have slack, switch to the next region.
        # We return NONE for this step because we cannot use Spot immediately after switching 
        # (we don't know if the new region has Spot until the next step).
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Round-Robin region switching
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        return ClusterType.NONE
