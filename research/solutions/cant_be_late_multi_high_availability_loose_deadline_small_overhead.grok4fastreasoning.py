import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "greedy_streak"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        self.num_regions = len(config["trace_files"])
        self.traces: List[List[bool]] = [None] * self.num_regions
        for i, path in enumerate(config["trace_files"]):
            with open(path, 'r') as tf:
                trace_data = json.load(tf)
                self.traces[i] = [bool(x) for x in trace_data]

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        gap = self.env.gap_seconds
        current_t = int(self.env.elapsed_seconds // gap)

        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        remaining_time = self.deadline - self.env.elapsed_seconds - self.remaining_restart_overhead

        if remaining_work > remaining_time:
            return ClusterType.ON_DEMAND

        # Compute streaks
        streaks = [0] * self.num_regions
        for r in range(self.num_regions):
            streak = 0
            for tt in range(current_t, len(self.traces[r])):
                if self.traces[r][tt]:
                    streak += 1
                else:
                    break
            streaks[r] = streak

        current_streak = streaks[current_region]
        if current_streak > 0:
            return ClusterType.SPOT

        # Find best other region
        best_r = -1
        best_streak = 0
        for r in range(self.num_regions):
            if r != current_region and streaks[r] > best_streak:
                best_streak = streaks[r]
                best_r = r

        if best_r != -1 and best_streak > 0:
            self.env.switch_region(best_r)
            return ClusterType.SPOT

        return ClusterType.ON_DEMAND