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

        # Load traces
        self.traces: List[List[bool]] = []
        self.trace_paths = config["trace_files"]
        for path in self.trace_paths:
            with open(path, 'r') as f:
                trace_data = json.load(f)
            # Assume trace_data is a list of 0/1 or bools; if dict, try 'availability'
            if isinstance(trace_data, dict):
                trace_list = trace_data.get("availability", [])
            else:
                trace_list = trace_data
            availability = [bool(x) for x in trace_list]
            self.traces.append(availability)

        self.num_regions = len(self.traces)
        if self.num_regions == 0:
            self.total_steps = 0
        else:
            self.total_steps = len(self.traces[0])

        # Precompute next spot per region per step
        self.next_spot_per_region: List[List[int]] = [[self.total_steps] * self.total_steps for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            last = self.total_steps
            for t in range(self.total_steps - 1, -1, -1):
                if self.traces[r][t]:
                    last = t
                self.next_spot_per_region[r][t] = last

        # Precompute global next spot step per starting step
        self.next_global: List[int] = [self.total_steps] * self.total_steps
        for t in range(self.total_steps):
            min_next = self.total_steps
            for r in range(self.num_regions):
                min_next = min(min_next, self.next_spot_per_region[r][t])
            self.next_global[t] = min_next

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_step = int(elapsed // gap)
        if current_step >= self.total_steps:
            return ClusterType.NONE

        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_wall = self.deadline - elapsed
        if remaining_wall <= 0:
            return ClusterType.NONE

        # Find candidates: regions with spot now, max streak
        max_streak = -1
        candidates = []
        look_ahead = min(50, self.total_steps - current_step)
        for r in range(self.num_regions):
            if not (current_step < len(self.traces[r]) and self.traces[r][current_step]):
                continue
            streak = 0
            for dt in range(look_ahead):
                t = current_step + dt
                if t >= len(self.traces[r]) or not self.traces[r][t]:
                    break
                streak += 1
            if streak > max_streak:
                max_streak = streak
                candidates = [r]
            elif streak == max_streak:
                candidates.append(r)

        if max_streak >= 0:
            # Choose best: prefer current if possible, else first
            best_r = min(candidates)
            if current_region in candidates:
                best_r = current_region
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            # No spot now, decide to wait or use ON_DEMAND
            next_step = self.next_global[current_step]
            if next_step < self.total_steps:
                wait_steps = next_step - current_step
                wait_seconds = wait_steps * gap
                buffer = 10 * self.restart_overhead
                if wait_seconds + remaining_work + buffer <= remaining_wall:
                    return ClusterType.NONE
            return ClusterType.ON_DEMAND