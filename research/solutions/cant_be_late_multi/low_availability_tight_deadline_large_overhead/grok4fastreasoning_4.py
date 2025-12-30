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

        trace_files = config["trace_files"]
        self.num_regions = self.env.get_num_regions()
        self.gap = self.env.gap_seconds
        self.availability: List[List[bool]] = []
        for tf in trace_files:
            with open(tf, 'r') as f:
                avail_list = json.load(f)
            self.availability.append([bool(x) for x in avail_list])
        self.num_steps = len(self.availability[0])

        self.streak: List[List[int]] = []
        for r in range(self.num_regions):
            streak = [0] * self.num_steps
            for t in range(self.num_steps - 1, -1, -1):
                if self.availability[r][t]:
                    streak[t] = 1 + (streak[t + 1] if t + 1 < self.num_steps else 0)
                else:
                    streak[t] = 0
            self.streak.append(streak)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_step = int(self.env.elapsed_seconds // self.gap)
        if current_step >= self.num_steps:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        current_r = self.env.get_current_region()
        best_r = -1
        best_streak = -1
        for r in range(self.num_regions):
            s = self.streak[r][current_step]
            if s > best_streak:
                best_streak = s
                best_r = r

        if best_streak > 0 and best_r != current_r:
            self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND