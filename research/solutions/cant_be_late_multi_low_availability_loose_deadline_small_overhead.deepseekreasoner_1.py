import json
from argparse import Namespace
from enum import Enum
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        # Initialize custom state
        self.gap = 3600.0  # default, can be overridden by env.gap_seconds
        self.switch_count = 0
        self.last_region = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Try to get actual gap from environment, fallback to default
        try:
            gap = self.env.gap_seconds
        except AttributeError:
            gap = self.gap

        # Calculate progress and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed

        # If already on-demand, stay there to avoid overhead
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        # Compute criticality: can we still finish if we switch to on-demand now?
        # We are not on on-demand, so switching incurs restart_overhead
        overhead = self.restart_overhead
        # Work possible in first timestep after switch
        first_work = max(0.0, gap - overhead)
        if remaining_work <= first_work:
            steps_needed = 1
        else:
            remaining_after_first = remaining_work - first_work
            steps_needed = 1 + math.ceil(remaining_after_first / gap)
        time_needed_on_demand = steps_needed * gap

        # If we cannot finish even with on-demand, we must still try
        critical = time_left < time_needed_on_demand

        # If critical, switch to on-demand immediately
        if critical:
            return ClusterType.ON_DEMAND

        # Not critical, prefer spot if available
        if has_spot:
            return ClusterType.SPOT
        else:
            # No spot in current region, try switching region
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            # Simple round‑robin
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            # Wait one timestep to see if new region has spot
            return ClusterType.NONE