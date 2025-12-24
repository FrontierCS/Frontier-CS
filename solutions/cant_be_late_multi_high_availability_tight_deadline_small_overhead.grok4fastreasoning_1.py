import json
from argparse import Namespace
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
        self.num_regions = len(config["trace_files"])
        self.availability_counts = [[0, 0] for _ in range(self.num_regions)]
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        self.availability_counts[current_region][0] += 1
        self.availability_counts[current_region][1] += int(has_spot)

        total_done = sum(self.task_done_time)
        if total_done >= self.task_duration:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_time <= 0:
            return ClusterType.NONE

        remaining_work = self.task_duration - total_done
        gap = self.env.gap_seconds
        approx_remaining_steps = (remaining_work + gap - 1) // gap
        approx_available_steps = remaining_time // gap
        safe_mode = (approx_available_steps < approx_remaining_steps + 3)

        if self.remaining_restart_overhead > 0:
            if last_cluster_type == ClusterType.SPOT and not has_spot:
                return ClusterType.ON_DEMAND
            else:
                if last_cluster_type == ClusterType.SPOT and not has_spot:
                    return ClusterType.ON_DEMAND
                return last_cluster_type

        if has_spot:
            return ClusterType.SPOT

        # no spot
        if safe_mode:
            return ClusterType.ON_DEMAND

        # choose best target
        best_prob = -1.0
        best_target = -1
        for r in range(self.num_regions):
            if r == current_region:
                continue
            seen = self.availability_counts[r][0]
            if seen == 0:
                prob = 0.5
            else:
                prob = self.availability_counts[r][1] / seen
            if prob > best_prob or (prob == best_prob and r < best_target):
                best_prob = prob
                best_target = r

        if best_target == -1:
            best_target = (current_region + 1) % self.num_regions

        self.env.switch_region(best_target)
        return ClusterType.ON_DEMAND
