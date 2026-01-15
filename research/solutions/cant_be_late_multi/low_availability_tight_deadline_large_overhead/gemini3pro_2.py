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
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        
        elapsed_time = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed_time
        
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate panic threshold
        # If we are close to the deadline, we must use On-Demand to guarantee completion.
        # We need enough time for remaining work + potential restart overhead.
        # We add a buffer (2 * gap) to ensure we switch safely before the absolute last moment,
        # accounting for the discrete time step granularity.
        panic_threshold = remaining_work + overhead + (2.0 * gap)
        
        if remaining_time < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # If not in panic mode, prioritize Spot instances
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is unavailable in current region and we have slack:
        # Switch to the next region to search for Spot capacity.
        # We return NONE for this step as we transition/wait.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        return ClusterType.NONE