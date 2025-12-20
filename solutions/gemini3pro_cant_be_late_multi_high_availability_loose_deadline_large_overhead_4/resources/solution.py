import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy that prioritizes Spot instances but 
    falls back to On-Demand to guarantee meeting the deadline."""

    NAME = "cant_be_late_strategy"

    def solve(self, spec_path: str) -> "Solution":
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
        # Calculate current progress and constraints
        done_time = sum(self.task_done_time)
        work_remaining = self.task_duration - done_time
        time_remaining = self.deadline - self.env.elapsed_seconds

        # Panic Threshold Calculation
        # We switch to On-Demand if the remaining time is close to the minimum time required.
        # min_time_needed includes:
        # 1. Actual work remaining
        # 2. Restart overhead (assumed incurred if we switch to OD)
        # 3. Safety buffer (2.5x step size) to handle discrete timesteps and ensure we don't 
        #    miss the deadline due to off-by-one errors or minor delays.
        
        safety_buffer = 2.5 * self.env.gap_seconds
        min_time_needed = work_remaining + self.restart_overhead + safety_buffer

        if time_remaining < min_time_needed:
            return ClusterType.ON_DEMAND

        # If we have sufficient slack, we prioritize Spot instances to save cost.
        if has_spot:
            return ClusterType.SPOT

        # If Spot is unavailable in the current region, we switch to the next region.
        # We iterate through regions in a round-robin fashion.
        num_regions = self.env.get_num_regions()
        current_region = self.env.get_current_region()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)

        # After switching, we don't know the Spot status of the new region for the current 
        # timestep. We return NONE to avoid errors and check status in the next step.
        return ClusterType.NONE
