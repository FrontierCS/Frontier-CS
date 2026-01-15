import json
from argparse import Namespace
from typing import List

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

        self.availability: List[List[bool]] = []
        for tf in config.get("trace_files", []):
            try:
                with open(tf, 'r') as f:
                    data = json.load(f)
                    self.availability.append([bool(x) for x in data])
            except:
                pass  # if load fails, empty
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        remaining_time = self.deadline - elapsed
        current_step = int(elapsed // gap)

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        if not self.availability or not self.availability or len(self.availability) == 0 or len(self.availability[0]) == 0:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Find best region
        best_score = -float('inf')
        best_region = current_region
        for r in range(num_regions):
            if r >= len(self.availability) or current_step >= len(self.availability[r]):
                continue
            total_potential = sum(1 for t in range(current_step, len(self.availability[r])) if self.availability[r][t])
            score = total_potential
            if r == current_region:
                score += 0.1  # small stay bonus
            else:
                score -= 0.05  # small switch penalty approx overhead
            if score > best_score:
                best_score = score
                best_region = r

        switched = False
        if best_region != current_region:
            self.env.switch_region(best_region)
            switched = True

        # Get current after possible switch
        current_r = self.env.get_current_region()

        # Get has_spot_new
        if current_r >= len(self.availability) or current_step >= len(self.availability[current_r]):
            has_spot_new = False
        else:
            has_spot_new = self.availability[current_r][current_step]

        if has_spot_new:
            return ClusterType.SPOT
        else:
            # Check if can wait for next spot in current region
            can_wait = False
            if (current_r < len(self.availability) and
                current_step + 1 < len(self.availability[current_r]) and
                self.availability[current_r][current_step + 1] and
                remaining_work <= remaining_time - gap):
                can_wait = True
            if can_wait:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND