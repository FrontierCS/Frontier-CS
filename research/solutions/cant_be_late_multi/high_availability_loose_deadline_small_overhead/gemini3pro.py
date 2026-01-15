import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cost-optimized multi-region scheduling strategy."""

    NAME = "slack_scavenger"

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
        Decide next action: use Spot if available, search other regions if not,
        or fallback to On-Demand if deadline is approaching.
        """
        elapsed = self.env.elapsed_seconds
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        remaining_time = self.deadline - elapsed
        
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate Panic Threshold:
        # If remaining_time falls below this threshold, we switch to On-Demand to guarantee completion.
        # Threshold = Work needed + Restart overhead + Safety Buffer.
        # Safety Buffer = 2 * step_size (gap) to handle time quantization and ensure we don't miss strictly.
        panic_threshold = remaining_work + overhead + (2.0 * gap)
        
        # 1. Panic Mode: Deadline tight -> Use Reliable Resource (On-Demand)
        if remaining_time < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Standard Mode: Deadline loose -> Optimize Cost
        if has_spot:
            # Best case: Spot available in current region
            return ClusterType.SPOT
        else:
            # Spot unavailable here, but we have slack time.
            # Strategy: "Scavenge" - Switch to next region and wait 1 step.
            # We return NONE to avoid paying for On-Demand or risking a blind Spot request.
            # In the next step, has_spot will indicate availability for the new region.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE