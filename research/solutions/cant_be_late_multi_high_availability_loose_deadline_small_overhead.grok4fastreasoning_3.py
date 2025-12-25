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
        self.gap = self.env.gap_seconds
        self.traces: List[List[bool]] = []
        for path in config["trace_files"]:
            with open(path, 'r') as tf:
                trace = json.load(tf)
            self.traces.append([bool(x) for x in trace])
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done_work = sum(self.task_done_time)
        if done_work >= self.task_duration:
            return ClusterType.NONE
        current_step = int(self.env.elapsed_seconds // self.gap)
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        best_streak = -1
        best_r = -1
        candidates = []
        if current_step < len(self.traces[current_region]) and self.traces[current_region][current_step]:
            candidates.append(current_region)
        for r in range(num_regions):
            if current_step < len(self.traces[r]) and self.traces[r][current_step]:
                candidates.append(r)
        for r in set(candidates):
            streak = 0
            t = current_step
            while t < len(self.traces[r]) and self.traces[r][t]:
                streak += 1
                t += 1
            if streak > best_streak:
                best_streak = streak
                best_r = r
        if best_r != -1:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND
