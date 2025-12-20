import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CantBeLateStrategy"  # REQUIRED: unique identifier

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
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-6:
            return ClusterType.NONE

        # Calculate time remaining
        time_remaining = self.deadline - self.env.elapsed_seconds

        # Determine overhead if we were to switch/start On-Demand now.
        # If we are already running On-Demand, we don't pay extra restart overhead
        # relative to continuing On-Demand (assuming stability).
        # If we are on Spot or None, switching to OD incurs overhead.
        switch_overhead = self.restart_overhead
        if last_cluster_type == ClusterType.ON_DEMAND:
            switch_overhead = 0.0

        # Define safety cushion.
        # We need to switch to OD *before* we run out of time to pay overhead and finish work.
        # We add a buffer of 2 time steps (gaps) to account for the current step resolution
        # and one potential failure/transition step.
        cushion = 2.0 * self.env.gap_seconds

        # Time required to finish if we switch to On-Demand immediately
        required_time = work_remaining + switch_overhead + cushion

        # 1. Safety Check: If we are close to the deadline, force On-Demand.
        # This ensures we don't risk Spot interruptions when time is critical.
        if time_remaining < required_time:
            return ClusterType.ON_DEMAND

        # 2. Cost Optimization: Prefer Spot if available and safe.
        if has_spot:
            return ClusterType.SPOT

        # 3. Search Mode: Spot unavailable in current region, but we have slack.
        # Switch to the next region and return NONE (pause) for this step.
        # Returning NONE allows the region switch to take effect without erroring on SPOT unavailable.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        return ClusterType.NONE
