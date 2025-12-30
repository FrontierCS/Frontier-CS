import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "streak_strategy"

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

        self.avail: List[List[bool]] = []
        for tf in config["trace_files"]:
            with open(tf, 'r') as f:
                trace = json.load(f)
            self.avail.append([bool(x) for x in trace])

        self.num_regions = len(self.avail)
        if self.num_regions > 0:
            self.total_steps = len(self.avail[0])
            self.streaks: List[List[int]] = []
            for r in range(self.num_regions):
                trace = self.avail[r]
                streak = [0] * self.total_steps
                if self.total_steps > 0 and trace[-1]:
                    streak[-1] = 1
                for t in range(self.total_steps - 2, -1, -1):
                    if trace[t]:
                        streak[t] = 1 + streak[t + 1]
                    else:
                        streak[t] = 0
                self.streaks.append(streak)
        else:
            self.total_steps = 0
            self.streaks = []

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        current_step = int(elapsed // gap)

        total_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_done
        if remaining_work <= 0:
            return ClusterType.NONE

        if self.total_steps == 0 or current_step >= self.total_steps:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        best_r = -1
        best_streak = -1
        for r in range(self.num_regions):
            if self.avail[r][current_step]:
                s = self.streaks[r][current_step]
                update = False
                if best_r == -1:
                    update = True
                elif s > best_streak:
                    update = True
                elif s == best_streak and r == current_region:
                    update = True
                if update:
                    best_r = r
                    best_streak = s

        if best_r != -1:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND