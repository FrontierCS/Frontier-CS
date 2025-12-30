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

        # Load traces
        self.traces = []
        trace_files = config.get("trace_files", [])
        self.num_regions = len(trace_files)
        gap = self.env.gap_seconds
        self.num_steps = int(self.deadline / gap) + 10  # margin

        for path in trace_files:
            with open(path, 'r') as tf:
                trace_data = json.load(tf)
            trace = [bool(x) for x in trace_data]
            if len(trace) < self.num_steps:
                trace += [False] * (self.num_steps - len(trace))
            self.traces.append(trace[:self.num_steps])

        # Precompute streaks
        self.streaks = []
        for r in range(self.num_regions):
            n = len(self.traces[r])
            streak = [0] * n
            for s in range(n - 2, -1, -1):
                if self.traces[r][s]:
                    streak[s] = 1 + streak[s + 1]
            self.streaks.append(streak)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        if current_time >= self.deadline:
            return ClusterType.NONE

        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE

        step_idx = min(int(current_time // self.env.gap_seconds), self.num_steps - 1)
        current_region = self.env.get_current_region()

        # Find best region with spot now (max streak)
        best_r = -1
        best_streak = -1
        for r in range(self.num_regions):
            if step_idx < len(self.traces[r]) and self.traces[r][step_idx]:
                strk = self.streaks[r][step_idx]
                if strk > best_streak:
                    best_streak = strk
                    best_r = r

        if best_r != -1:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            # No spot available anywhere, use on-demand
            return ClusterType.ON_DEMAND