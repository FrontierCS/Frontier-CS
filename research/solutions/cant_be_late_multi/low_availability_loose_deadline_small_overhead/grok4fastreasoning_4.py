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

        self.traces: List[List[bool]] = []
        self.streaks: List[List[int]] = []
        self.num_regions = len(config["trace_files"])
        for path in config["trace_files"]:
            with open(path, 'r') as tf:
                trace = json.load(tf)
            self.traces.append(trace)

            n = len(trace)
            streaks_r = [0] * n
            if n > 0 and trace[n - 1]:
                streaks_r[n - 1] = 1
            for t in range(n - 2, -1, -1):
                if trace[t]:
                    streaks_r[t] = 1 + streaks_r[t + 1]
            self.streaks.append(streaks_r)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        current_step = int(elapsed // self.env.gap_seconds)
        done = sum(self.task_done_time)
        if done >= self.task_duration or elapsed >= self.deadline:
            return ClusterType.NONE

        if current_step >= len(self.traces[current_region]):
            return ClusterType.ON_DEMAND

        current_has_spot = self.traces[current_region][current_step]
        if current_has_spot:
            return ClusterType.SPOT

        max_streak = 0
        best_r = current_region
        for r in range(self.num_regions):
            if current_step >= len(self.traces[r]):
                continue
            streak = self.streaks[r][current_step]
            if streak > max_streak:
                max_streak = streak
                best_r = r

        if max_streak > 0:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND