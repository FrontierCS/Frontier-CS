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
        # Current state
        current_time = self.env.elapsed_seconds
        total_done = sum(self.task_done_time)
        needed_work = self.task_duration - total_done

        # If task is complete (or effectively complete)
        if needed_work <= 1e-6:
            return ClusterType.NONE

        time_remaining = self.deadline - current_time
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Calculate slack: Time available minus time needed to work and one restart overhead
        slack = time_remaining - needed_work - overhead

        # Panic threshold: Minimum slack required to feel safe relying on Spot or searching.
        # We keep a buffer of 1.5 steps (gap) plus overhead to handle transitions safely.
        panic_threshold = (gap * 1.5) + overhead

        # 1. Critical Deadline Protection
        # If slack is below the safe threshold, we must use On-Demand to guarantee completion.
        if slack < panic_threshold:
            return ClusterType.ON_DEMAND

        # 2. Cost Optimization
        # If we have slack and Spot is available, use it.
        if has_spot:
            return ClusterType.SPOT

        # 3. Region Exploration
        # If Spot is unavailable in current region, but we have plenty of slack,
        # switch to another region and wait (NONE) for the next step.
        # We pay 'gap' time to search. Ensure we still have enough slack after paying 'gap'.
        if slack > (panic_threshold + gap):
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                current_region = self.env.get_current_region()
                # Round-robin switch
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
            return ClusterType.NONE

        # 4. Fallback
        # Spot is unavailable and we don't have enough slack to search.
        # Must run now to meet deadline, so use On-Demand.
        return ClusterType.ON_DEMAND
