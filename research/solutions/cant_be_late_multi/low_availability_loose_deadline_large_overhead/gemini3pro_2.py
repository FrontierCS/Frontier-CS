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
        # Calculate remaining work
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        
        # If task is effectively done, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Time remaining until deadline
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Determine overhead cost if we force a switch to On-Demand.
        # If currently On-Demand, we don't pay overhead to stay (unless interrupted).
        # If Spot or None, we would pay overhead to start On-Demand.
        overhead_penalty = self.restart_overhead
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_penalty = 0.0

        # Safety Buffer:
        # We need a margin to handle the discrete time steps (gap_seconds).
        # We use 2.0 * gap_seconds to ensure we react before it's too late.
        buffer = 2.0 * self.env.gap_seconds
        
        # Panic Threshold:
        # If time left is close to the minimum time needed to finish on OD,
        # we must switch to OD immediately to guarantee the deadline.
        safe_threshold = remaining_work + overhead_penalty + buffer
        
        if time_left < safe_threshold:
            return ClusterType.ON_DEMAND

        # If we have slack, prioritize cost savings (Spot)
        if has_spot:
            return ClusterType.SPOT
        
        # Spot is unavailable in current region, but we have slack.
        # Switch to the next region to try and find Spot availability.
        # We return NONE for this step as we switch regions.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        return ClusterType.NONE