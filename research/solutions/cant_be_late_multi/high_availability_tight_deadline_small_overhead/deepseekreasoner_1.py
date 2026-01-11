import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "simple_conservative"

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
        # Initialize state variables
        self._in_on_demand_streak = 0
        self._current_region = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update streak counter
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._in_on_demand_streak += 1
        else:
            self._in_on_demand_streak = 0

        # Compute remaining work and time
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds

        # Compute time needed if we switch to on-demand now
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Already on on-demand, no overhead
            steps_needed = math.ceil(remaining_work / gap)
            time_needed_on_demand = steps_needed * gap
        else:
            # Would incur overhead
            first_step_work = gap - self.restart_overhead
            if remaining_work <= first_step_work:
                time_needed_on_demand = gap
            else:
                remaining_after_first = remaining_work - first_step_work
                full_steps = math.ceil(remaining_after_first / gap)
                time_needed_on_demand = (1 + full_steps) * gap

        # Safety buffer: 2 hours
        buffer = 2 * gap

        # If already committed to on-demand, stay there
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        # If running out of time, switch to on-demand
        if time_left < time_needed_on_demand + buffer:
            return ClusterType.ON_DEMAND

        # Otherwise, try to use spot if available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide between pausing or on-demand
        # Use on-demand only if buffer is small
        if time_left - time_needed_on_demand >= 4 * gap:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND