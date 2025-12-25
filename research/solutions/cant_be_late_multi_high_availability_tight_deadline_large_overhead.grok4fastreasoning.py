import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "spot_hunter"

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

        trace_files = config.get("trace_files", [])
        num_regions = self.env.get_num_regions()
        self.availability = []
        for i in range(num_regions):
            path = trace_files[i]
            with open(path, 'r') as f:
                trace = json.load(f)
            self.availability.append([bool(x) for x in trace])
        self.num_steps = len(self.availability[0]) if self.availability else 0

        self.streaks = [[0] * self.num_steps for _ in range(num_regions)]
        for r in range(num_regions):
            streak = 0
            for s in range(self.num_steps - 1, -1, -1):
                if self.availability[r][s]:
                    streak += 1
                else:
                    streak = 0
                self.streaks[r][s] = streak

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        if current_step >= self.num_steps:
            return ClusterType.ON_DEMAND

        max_streak = 0
        best_r = current_region
        if self.availability[current_region][current_step]:
            max_streak = self.streaks[current_region][current_step]
            best_r = current_region

        for r in range(num_regions):
            if r == current_region:
                continue
            if self.availability[r][current_step]:
                s = self.streaks[r][current_step]
                if s > max_streak:
                    max_streak = s
                    best_r = r

        if max_streak > 0:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND
