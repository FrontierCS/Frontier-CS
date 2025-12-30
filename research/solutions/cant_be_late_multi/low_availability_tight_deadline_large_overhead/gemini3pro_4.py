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
        # Calculate current state metrics
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        rem_work = max(0.0, self.task_duration - done)
        rem_time = self.deadline - elapsed
        overhead = self.restart_overhead
        
        # Safety Logic: Determine if we must use On-Demand to guarantee completion.
        # We calculate the time required to finish if we switch to/continue OD now.
        # If we are already running OD, we don't incur new overhead.
        # If we are not running OD, we assume we need to pay overhead to start it.
        needed_time = rem_work
        if last_cluster_type != ClusterType.ON_DEMAND:
            needed_time += overhead
            
        # Safety Buffer: 30 minutes (1800 seconds).
        # If remaining time is close to required time, force OD.
        # This prevents missing the hard deadline which has a massive penalty.
        SAFETY_BUFFER = 1800.0
        
        if rem_time < needed_time + SAFETY_BUFFER:
            return ClusterType.ON_DEMAND

        # Cost Optimization Logic:
        # If we have slack, we prioritize Spot instances to minimize cost.
        if has_spot:
            return ClusterType.SPOT
            
        # Multi-Region Logic:
        # If Spot is unavailable in the current region, we switch to the next region.
        # We cycle through regions in a round-robin fashion.
        # We return ClusterType.NONE for the current step because:
        # 1. We cannot check Spot availability in the new region until the next step.
        # 2. Returning SPOT blindly is forbidden if availability is unknown/False.
        # 3. Time spent in NONE allows us to 'search' with only time cost (no monetary cost).
        curr_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (curr_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        return ClusterType.NONE