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
        # Calculate progress
        done_time = sum(self.task_done_time)
        remaining_work = self.task_duration - done_time

        # If task is effectively finished, do nothing
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate slack
        # We treat 'needed_time' as work remaining plus one restart overhead
        # to account for the cost of starting/restarting.
        needed_time = remaining_work + self.restart_overhead
        slack = time_left - needed_time
        
        # Panic Threshold:
        # If slack drops below a safe buffer, switch to On-Demand to guarantee completion.
        # Buffer includes:
        # - 2.0 * gap_seconds: Buffer against losing a step (e.g. preemption at end of hour) 
        #   and having margin for the next.
        # - 3.0 * restart_overhead: Buffer for multiple restart overheads.
        panic_threshold = 2.0 * self.env.gap_seconds + 3.0 * self.restart_overhead

        # Critical condition: Not enough slack to risk Spot
        if slack < panic_threshold:
            return ClusterType.ON_DEMAND
        
        # Normal operation: Prefer Spot
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is unavailable in current region and we have slack:
        # Switch to the next region and wait one step (NONE) to probe availability.
        # We cycle through regions in a round-robin fashion.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        # Return NONE because we cannot guarantee Spot availability in the new region 
        # immediately without risking an error if it's unavailable. 
        # We accept the time cost of one step to find a better region.
        return ClusterType.NONE
