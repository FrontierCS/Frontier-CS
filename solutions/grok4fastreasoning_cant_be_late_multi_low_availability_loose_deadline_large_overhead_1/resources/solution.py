import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)
        self.trace_paths = config["trace_files"]
        self.num_regions = len(self.trace_paths)
        self.traces = []
        for path in self.trace_paths:
            with open(path, 'r') as tf:
                trace = json.load(tf)
                self.traces.append([bool(x) for x in trace])
        self.total_steps = len(self.traces[0])
        self.streaks = []
        for r in range(self.num_regions):
            streak = [0] * self.total_steps
            for t in range(self.total_steps - 1, -1, -1):
                if self.traces[r][t]:
                    next_streak = streak[t + 1] if t + 1 < self.total_steps else 0
                    streak[t] = 1 + next_streak
            self.streaks.append(streak)
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE
        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        if current_step >= self.total_steps:
            return ClusterType.NONE
        remaining_work = self.task_duration - progress
        remaining_time = self.deadline - self.env.elapsed_seconds
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        effective_remaining_time = remaining_time
        if remaining_work > effective_remaining_time:
            return ClusterType.ON_DEMAND
        current_region = self.env.get_current_region()
        if has_spot:
            return ClusterType.SPOT
        if remaining_time < remaining_work + self.restart_overhead:
            return ClusterType.ON_DEMAND
        best_streak = 0
        best_r = -1
        for r in range(self.num_regions):
            if self.traces[r][current_step]:
                this_streak = self.streaks[r][current_step]
                if this_streak > best_streak:
                    best_streak = this_streak
                    best_r = r
        min_streak_req = max(1, int(self.restart_overhead / self.env.gap_seconds) + 1)
        if best_r != -1 and best_streak >= min_streak_req:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND
