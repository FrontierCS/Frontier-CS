import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        # Current state
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        needed = self.task_duration - done
        
        # If task is effectively done
        if needed <= 0:
            return ClusterType.NONE

        time_left = self.deadline - elapsed
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate slack: Time remaining minus (Work needed + potential Restart Overhead)
        # We subtract overhead conservatively to ensure we can afford a restart if needed.
        slack = time_left - (needed + overhead)
        
        # Safety buffer: maintain enough slack to tolerate decision granularity (gap)
        # and some margin. If slack drops below this, we force stable execution (On-Demand).
        safety_buffer = 2.0 * gap

        if has_spot:
            # Spot is available.
            # Optimization: If we are currently running On-Demand and very close to finishing,
            # switching to Spot might cost more time in overhead than it saves/makes progress.
            # If remaining work is less than 2x overhead, just finish on On-Demand.
            if (last_cluster_type == ClusterType.ON_DEMAND and 
                needed < overhead * 2.0):
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            if slack > safety_buffer:
                # We have ample time.
                num_regions = self.env.get_num_regions()
                if num_regions > 1:
                    # Strategy: Switch to next region and pause (NONE) to check availability.
                    # This "polls" regions at the cost of time (gap), saving money compared to OD.
                    current_idx = self.env.get_current_region()
                    next_idx = (current_idx + 1) % num_regions
                    self.env.switch_region(next_idx)
                    return ClusterType.NONE
                else:
                    # Single region case: Wait for Spot to recover to save money.
                    return ClusterType.NONE
            else:
                # Slack is critical. Must use On-Demand to ensure deadline is met.
                return ClusterType.ON_DEMAND