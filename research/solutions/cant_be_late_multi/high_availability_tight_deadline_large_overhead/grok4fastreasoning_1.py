import json
from argparse import Namespace
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

        trace_files = config["trace_files"]
        self.num_regions = len(trace_files)
        self.availability = []
        for path in trace_files:
            with open(path, 'r') as f:
                trace = json.load(f)
            self.availability.append([bool(x) for x in trace])
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if sum(self.task_done_time) >= self.task_duration:
            return ClusterType.NONE

        step = int(round(self.env.elapsed_seconds / self.env.gap_seconds))
        current_region = self.env.get_current_region()
        num_regions = self.num_regions
        max_steps = len(self.availability[0]) if self.availability else 0

        if step >= max_steps:
            return ClusterType.ON_DEMAND

        # Prefer current region if possible
        best_r = current_region
        best_streak = 0
        if step < len(self.availability[current_region]) and self.availability[current_region][step]:
            streak = 0
            for s in range(step, len(self.availability[current_region])):
                if not self.availability[current_region][s]:
                    break
                streak += 1
            best_streak = streak
        else:
            best_r = -1
            best_streak = 0

        # Check other regions for better streak
        for r in range(num_regions):
            if r == current_region:
                continue
            if step >= len(self.availability[r]) or not self.availability[r][step]:
                continue
            streak = 0
            for s in range(step, len(self.availability[r])):
                if not self.availability[r][s]:
                    break
                streak += 1
            if streak > best_streak:
                best_streak = streak
                best_r = r

        if best_streak > 0:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND