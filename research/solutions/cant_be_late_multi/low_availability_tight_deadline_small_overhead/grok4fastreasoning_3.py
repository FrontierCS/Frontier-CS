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
        for tf in trace_files:
            with open(tf, 'r') as f:
                trace = json.load(f)
            self.availability.append(trace)
        self.total_steps = len(self.availability[0]) if self.availability else 0
        self.streak = [[0] * self.total_steps for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            av = self.availability[r]
            n = self.total_steps
            s = self.streak[r]
            if n > 0 and av[n - 1]:
                s[n - 1] = 1
            for i in range(n - 2, -1, -1):
                if av[i]:
                    s[i] = 1 + s[i + 1]
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_step = int(elapsed // gap)

        if current_step >= self.total_steps:
            return ClusterType.NONE

        if has_spot:
            return ClusterType.SPOT

        # Find best region with spot available now
        max_streak = 0
        best_r = -1
        for r in range(self.num_regions):
            if self.availability[r][current_step]:
                st = self.streak[r][current_step]
                if st > max_streak or (st == max_streak and (best_r == -1 or r < best_r)):
                    max_streak = st
                    best_r = r

        min_streak_threshold = 100
        if max_streak >= min_streak_threshold and best_r != -1:
            self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND