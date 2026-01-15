import json
from argparse import Namespace
from typing import Dict

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

        self.num_regions = len(config.get("trace_files", []))
        self.min_steps_per_region = 20
        self.step_counts: Dict[int, int] = {i: 0 for i in range(self.num_regions)}
        self.spot_counts: Dict[int, int] = {i: 0 for i in range(self.num_regions)}
        self.phase = "exploration"
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current = self.env.get_current_region()

        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        time_remaining = self.deadline - self.env.elapsed_seconds
        pending_overhead = self.remaining_restart_overhead
        safety_factor = 1.1
        safe_mode = (time_remaining - pending_overhead < remaining_work * safety_factor)

        switched = False
        if not safe_mode:
            if self.phase == "exploration":
                steps = self.step_counts[current]
                all_sampled = all(self.step_counts[r] >= self.min_steps_per_region for r in range(self.num_regions))
                if all_sampled:
                    self.phase = "exploitation"
                elif steps >= self.min_steps_per_region:
                    next_r = (current + 1) % self.num_regions
                    self.env.switch_region(next_r)
                    switched = True
            elif self.phase == "exploitation":
                current_steps = self.step_counts[current]
                current_est = self.spot_counts[current] / current_steps if current_steps > 0 else 0.0
                best_r = current
                best_est = current_est
                for r in range(self.num_regions):
                    rs = self.step_counts[r]
                    if rs >= self.min_steps_per_region:
                        est = self.spot_counts[r] / rs
                        if est > best_est + 0.05:
                            best_est = est
                            best_r = r
                if best_r != current:
                    self.env.switch_region(best_r)
                    switched = True

            if not switched:
                self.step_counts[current] += 1
                if has_spot:
                    self.spot_counts[current] += 1

        if safe_mode:
            return ClusterType.ON_DEMAND
        elif switched:
            return ClusterType.ON_DEMAND
        elif has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND