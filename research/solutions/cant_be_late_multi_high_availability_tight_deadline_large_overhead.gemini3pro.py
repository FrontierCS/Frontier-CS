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
        # 1. Calculate remaining work and time
        done = sum(self.task_done_time)
        remaining = self.task_duration - done

        # If effectively finished, return NONE (env should handle termination)
        if remaining <= 1e-6:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # 2. Calculate Slack
        # Slack is the time buffer we have assuming we switch to OD immediately.
        # We subtract overhead because starting OD (or any new instance) incurs it.
        # If we are already running OD, the env won't charge overhead, but for safety
        # we calculate slack conservatively assuming a potential restart.
        slack = time_left - remaining - overhead

        # 3. Critical Threshold for Safety
        # If we use Spot and it fails (or we wait), we lose 'gap' time.
        # We also face the risk of needing another restart overhead.
        # If slack is less than gap + overhead, we are in danger of missing the deadline
        # if anything goes wrong. We force OD to ensure completion.
        # Added small buffer (10s) for float precision.
        critical_threshold = gap + overhead + 10.0

        if slack < critical_threshold:
            return ClusterType.ON_DEMAND

        # 4. Standard Decision Logic
        if has_spot:
            # We have enough slack, and Spot is available. Use it to save cost.
            return ClusterType.SPOT
        
        # 5. Search Logic
        # Spot is unavailable in current region.
        # We can switch regions and wait (ClusterType.NONE) to find Spot.
        # Switching costs 1 'gap' of time (since we return NONE for this step).
        # We check if we have enough slack to afford this search cost.
        # We want to ensure that after wasting 'gap' time, we still have positive slack.
        if slack > gap + 10.0:
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            # Simple Round-Robin search to find an available region
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            return ClusterType.NONE
        
        # 6. Fallback
        # Spot unavailable and not enough slack to search -> Force OD.
        return ClusterType.ON_DEMAND