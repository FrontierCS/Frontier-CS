import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CantBeLateStrategy"

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
        Strategy:
        1. Panic Mode: If time is running out (close to required time + overhead), force On-Demand.
        2. Greedy Mode: If Spot is available, use it.
        3. Search Mode: If Spot unavailable, switch region and wait (NONE) to save cost.
        """
        # Calculate remaining work
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        
        # Check if task is already done
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Calculate time metrics
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # 1. Panic Mode Check
        # Calculate minimum time required to finish guarantees: remaining work + restart overhead.
        # Add a safety margin (2.0 * gap) to account for step quantization and overheads.
        # If we are within this window, we must use On-Demand to guarantee completion.
        safety_threshold = remaining_work + overhead + (2.0 * gap)
        
        if time_left < safety_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Greedy / Search Mode
        if has_spot:
            # Spot is available and we have slack time. Use Spot for cost savings.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region and we have slack.
            # Switch to the next region (round-robin) to check availability in the next step.
            # Return NONE to pause execution and avoid paying OD costs while searching.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE