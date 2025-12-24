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

        # Load availability traces
        self.availability: List[List[bool]] = []
        trace_files = config.get("trace_files", [])
        self.num_regions = len(trace_files)
        for path in trace_files:
            try:
                with open(path, 'r') as f:
                    trace_data = json.load(f)
                trace = [bool(x) for x in trace_data]
                self.availability.append(trace)
            except:
                # Fallback empty if load fails
                self.availability.append([])

        if self.availability:
            self.total_steps = len(self.availability[0])
            # Precompute streaks for each region and step
            self.streaks: List[List[int]] = []
            for r in range(self.num_regions):
                trace = self.availability[r]
                n = len(trace)
                if n == 0:
                    self.streaks.append([])
                    continue
                next_int = [0] * n
                if not trace[n-1]:
                    next_int[n-1] = n - 1
                else:
                    next_int[n-1] = n
                for t in range(n-2, -1, -1):
                    if not trace[t]:
                        next_int[t] = t
                    else:
                        next_int[t] = next_int[t + 1]
                streak = [next_int[t] - t for t in range(n)]
                self.streaks.append(streak)
        else:
            self.total_steps = 0
            self.streaks = []

        self.gap = self.env.gap_seconds if hasattr(self.env, 'gap_seconds') else 3600.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE

        current_step = int(self.env.elapsed_seconds / self.gap)
        if current_step >= self.total_steps or self.total_steps == 0:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        current_streak = self.streaks[current_region][current_step] if current_step < len(self.streaks[current_region]) else 0

        max_streak = current_streak
        best_r = current_region
        for r in range(self.num_regions):
            if r == current_region:
                continue
            if current_step >= len(self.streaks[r]):
                s = 0
            else:
                s = self.streaks[r][current_step]
            if s > max_streak:
                max_streak = s
                best_r = r

        if best_r != current_region:
            self.env.switch_region(best_r)

        if max_streak > 0:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND
