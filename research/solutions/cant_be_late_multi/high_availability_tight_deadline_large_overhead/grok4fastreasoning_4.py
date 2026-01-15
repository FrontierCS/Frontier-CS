import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"  # REQUIRED: unique identifier

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

        # Load traces
        self.availability = []
        self.trace_files = config.get("trace_files", [])
        for path in self.trace_files:
            with open(path, 'r') as f:
                trace = json.load(f)
                self.availability.append([bool(x) for x in trace])
        self.num_regions = len(self.availability)
        if self.num_regions > 0:
            self.trace_length = len(self.availability[0])
            self.streaks = []
            for trace in self.availability:
                n = len(trace)
                streak = [0] * n
                for t in range(n - 1, -1, -1):
                    if trace[t]:
                        streak[t] = 1 + (streak[t + 1] if t + 1 < n else 0)
                self.streaks.append(streak)

        # Init progress
        self.total_progress = sum(self.task_done_time)
        self.last_len = len(self.task_done_time)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update progress
        current_len = len(self.task_done_time)
        if current_len > self.last_len:
            self.total_progress += sum(self.task_done_time[self.last_len:current_len])
        self.last_len = current_len

        if self.total_progress >= self.task_duration - 1e-6:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)

        if has_spot:
            return ClusterType.SPOT

        # No spot in current, find best region with spot now and longest streak
        max_streak = -1
        best_r = current_region
        for r in range(self.num_regions):
            if current_step >= self.trace_length or not self.availability[r][current_step]:
                continue
            s = self.streaks[r][current_step]
            if s > max_streak:
                max_streak = s
                best_r = r

        if max_streak > 0 and best_r != current_region:
            self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND