import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "multi_streak"

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
        self.avail: List[List[bool]] = []
        for path in trace_files:
            with open(path, 'r') as ff:
                data = json.load(ff)
            self.avail.append([bool(x) for x in data])
        assert len(self.avail) == self.num_regions

        N = len(self.avail[0]) if self.avail else 0
        for a in self.avail:
            assert len(a) == N

        self.gap_seconds = self.env.gap_seconds

        # Precompute streaks
        self.streaks: List[List[int]] = []
        for r in range(self.num_regions):
            L = N
            streak = [0] * L
            for t in range(L - 1, -1, -1):
                if self.avail[r][t]:
                    next_streak = streak[t + 1] if t + 1 < L else 0
                    streak[t] = 1 + next_streak
            self.streaks.append(streak)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        current_step = int(self.env.elapsed_seconds // self.gap_seconds)
        if current_step >= len(self.streaks[0]):
            return ClusterType.ON_DEMAND

        # Get current streak
        current_streak = 0
        if current_step < len(self.streaks[current_region]):
            current_streak = self.streaks[current_region][current_step]
        max_streak = current_streak
        chosen_r = current_region if current_streak > 0 else None

        # Find better
        for r in range(self.num_regions):
            if r == current_region:
                continue
            if current_step < len(self.streaks[r]):
                s = self.streaks[r][current_step]
                if s > max_streak:
                    max_streak = s
                    chosen_r = r

        if chosen_r is not None:
            if chosen_r != current_region:
                self.env.switch_region(chosen_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND
