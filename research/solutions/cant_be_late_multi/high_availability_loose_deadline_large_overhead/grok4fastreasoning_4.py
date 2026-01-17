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

        self.num_regions = len(config["trace_files"])
        self.traces: List[List[bool]] = [None] * self.num_regions
        for i, path in enumerate(config["trace_files"]):
            with open(path, 'r') as tf:
                trace_data = json.load(tf)
                if isinstance(trace_data, dict) and "availability" in trace_data:
                    self.traces[i] = trace_data["availability"]
                else:
                    self.traces[i] = trace_data

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        task_duration = self.task_duration
        task_done_time = self.task_done_time

        done_work = sum(task_done_time)
        remaining_work = task_duration - done_work
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        step_idx = int(elapsed // gap)

        if has_spot:
            return ClusterType.SPOT

        # Find best region with spot available this step
        best_r = -1
        max_streak = -1
        for r in range(self.num_regions):
            if r == current_region:
                continue
            if step_idx >= len(self.traces[r]) or not self.traces[r][step_idx]:
                continue
            # Compute streak
            streak = 0
            max_possible = min(step_idx + 48, len(self.traces[r]))  # limit for efficiency
            for s in range(step_idx, max_possible):
                if self.traces[r][s]:
                    streak += 1
                else:
                    break
            if streak > max_streak:
                max_streak = streak
                best_r = r

        if best_r != -1:
            self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.NONE