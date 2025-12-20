"""
Example solution for cant-be-late-multi problem.

Solution interface:
    class Solution(MultiRegionStrategy):
        def solve(self, spec_path: str) -> "Solution":
            # Read config from spec_path and initialize
            return self

        def _step(self, last_cluster_type, has_spot) -> ClusterType:
            # Decision logic at each simulation step
            ...
"""
import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Greedy multi-region strategy: use spot when available, switch regions if not."""

    NAME = "greedy_multi_region"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
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
        """Make decision at each simulation step."""
        env = self.env
        gap = env.gap_seconds

        work_left = self.task_duration - sum(self.task_done_time)
        if work_left <= 1e-9:
            return ClusterType.NONE

        left_ticks = max(0, math.floor((self.deadline - env.elapsed_seconds) / gap))
        need1d = math.ceil((work_left + self.restart_overhead) / gap)
        need2d = math.ceil((work_left + 2 * self.restart_overhead) / gap)

        # Must switch to on-demand if we can't afford any more preemptions
        if need1d >= left_ticks:
            return ClusterType.ON_DEMAND

        # Should be cautious if we can only afford one more preemption
        if need2d >= left_ticks:
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Normal operation - try spot
        if has_spot:
            return ClusterType.SPOT

        # No spot in current region, try switching regions
        num_regions = env.get_num_regions()
        current_region = env.get_current_region()

        for i in range(num_regions):
            next_region = (current_region + 1 + i) % num_regions
            if next_region != current_region:
                env.switch_region(next_region)
                return ClusterType.NONE

        # No other regions to try, just wait
        return ClusterType.NONE
