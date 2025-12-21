import json
import math
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

        # Load spot traces
        self.spot_traces = []
        trace_files = config.get("trace_files", [])
        self.num_regions = len(trace_files)
        for path in trace_files:
            with open(path, 'r') as tf:
                data = json.load(tf)
                trace = [bool(x) for x in data]
                self.spot_traces.append(trace)
        if self.num_regions > 0:
            self.max_t = len(self.spot_traces[0])
            # Precompute streaks
            self.streaks = [[0] * self.max_t for _ in range(self.num_regions)]
            for r in range(self.num_regions):
                for t in range(self.max_t - 1, -1, -1):
                    if self.spot_traces[r][t]:
                        next_streak = self.streaks[r][t + 1] if t + 1 < self.max_t else 0
                        self.streaks[r][t] = 1 + next_streak
                    else:
                        self.streaks[r][t] = 0
            # Precompute has_any
            has_any = [False] * self.max_t
            for t in range(self.max_t):
                has_any[t] = any(self.spot_traces[r][t] for r in range(self.num_regions))
            # Precompute next_spot
            self.next_spot = [self.max_t] * self.max_t
            for t in range(self.max_t - 1, -1, -1):
                if has_any[t]:
                    self.next_spot[t] = t
                elif t + 1 < self.max_t:
                    self.next_spot[t] = self.next_spot[t + 1]
        else:
            self.max_t = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        current_step = round(elapsed / gap)
        if current_step >= self.max_t:
            return ClusterType.ON_DEMAND

        current_r = self.env.get_current_region()

        # Find best region for spot
        max_streak = 0
        best_r = current_r
        curr_streak = self.streaks[current_r][current_step]
        if curr_streak > 0:
            max_streak = curr_streak
            best_r = current_r
        for r in range(self.num_regions):
            if r == current_r:
                continue
            s = self.streaks[r][current_step]
            if s > max_streak:
                max_streak = s
                best_r = r

        if max_streak > 0:
            if best_r != current_r:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            # No spot now, decide to wait or on-demand
            next_t = self.next_spot[current_step]
            if next_t >= self.max_t:
                return ClusterType.ON_DEMAND
            wait_steps = next_t - current_step
            wait_wall = wait_steps * gap
            remaining_work_sec = self.task_duration - sum(self.task_done_time)
            remaining_wall_sec = self.deadline - elapsed
            if remaining_work_sec + self.remaining_restart_overhead + wait_wall <= remaining_wall_sec:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
