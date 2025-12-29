import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "solution_strategy"

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
        done_time = sum(self.task_done_time)
        needed_time = self.task_duration - done_time

        # Check if task is essentially done
        if needed_time <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed

        # Safety Threshold Logic:
        # We must switch to On-Demand if the deadline is approaching.
        # We add a safety buffer (2 hours) plus the restart overhead to ensure
        # we have enough time to finish even if we are currently interrupted.
        safety_buffer = 7200.0  # 2 hours in seconds
        time_required_worst_case = needed_time + self.restart_overhead

        if remaining_time < (time_required_worst_case + safety_buffer):
            return ClusterType.ON_DEMAND

        # Cost Minimization Logic:
        # If we have slack, we prioritize Spot instances.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable in the current region.
            # We switch to the next region in a round-robin fashion.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions

            self.env.switch_region(next_region)

            # We return NONE for this timestep. 
            # This pauses execution (costing 0 money, but consuming time slack)
            # to check availability in the new region during the next timestep.
            return ClusterType.NONE