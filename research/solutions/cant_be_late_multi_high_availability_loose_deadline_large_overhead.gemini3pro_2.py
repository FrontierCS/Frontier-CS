import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "AdaptiveSpotStrategy"

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
        1. Check if we are close to the deadline. If so, force On-Demand to guarantee completion.
        2. If we have slack, prefer Spot instances.
        3. If Spot is unavailable in the current region, switch to the next region and wait (NONE).
        """
        # Current state variables
        elapsed = self.env.elapsed_seconds
        done_work = sum(self.task_done_time)
        needed_work = self.task_duration - done_work
        remaining_time = self.deadline - elapsed
        gap = self.env.gap_seconds

        # 1. Deadline Safety Check
        # Calculate time required to finish if we use On-Demand starting now.
        # If we are already on On-Demand, we just need to finish the pending overhead + work.
        # If we switch to On-Demand, we incur the full restart overhead.
        if last_cluster_type == ClusterType.ON_DEMAND:
            time_to_finish_od = needed_work + self.remaining_restart_overhead
        else:
            time_to_finish_od = needed_work + self.restart_overhead

        # Safety buffer to account for step granularity and potential edge cases.
        # 2.0 * gap_seconds ensures we switch to OD with at least 2 steps of wiggle room.
        safety_buffer = 2.0 * gap

        if remaining_time < (time_to_finish_od + safety_buffer):
            return ClusterType.ON_DEMAND

        # 2. Cost Optimization (Spot Usage)
        if has_spot:
            return ClusterType.SPOT

        # 3. Spot Unavailable Strategy
        # If Spot is not available in the current region, we switch to another region.
        # We use a round-robin approach to cycle through regions.
        # We return NONE for this step because we cannot verify Spot availability
        # in the new region until the next step.
        curr_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (curr_region + 1) % num_regions

        self.env.switch_region(next_region)
        return ClusterType.NONE