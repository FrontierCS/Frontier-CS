import json
import math
from argparse import Namespace
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

        self.gap = self.env.gap_seconds
        self.T = math.ceil(self.deadline / self.gap) + 1
        self.availability = []
        trace_files = config.get("trace_files", [])
        for path in trace_files:
            with open(path, 'r') as f:
                data = json.load(f)
            trace = []
            for x in data:
                if isinstance(x, int):
                    trace.append(x != 0)
                elif isinstance(x, bool):
                    trace.append(x)
                else:
                    trace.append(False)
            if len(trace) < self.T:
                trace += [False] * (self.T - len(trace))
            else:
                trace = trace[:self.T]
            self.availability.append(trace)
        self.num_regions = len(self.availability)

        self.streaks = []
        for r in range(self.num_regions):
            streaks_r = [0] * self.T
            for tt in range(self.T - 1, -1, -1):
                if self.availability[r][tt]:
                    streaks_r[tt] = 1 + (streaks_r[tt + 1] if tt + 1 < self.T else 0)
            self.streaks.append(streaks_r)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.env.elapsed_seconds >= self.deadline:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        current_t = int(self.env.elapsed_seconds // self.gap)

        current_streak = 0
        if current_t < self.T and self.availability[current_region][current_t]:
            current_streak = self.streaks[current_region][current_t]

        max_streak = 0
        best_r = current_region
        for r in range(self.num_regions):
            if current_t < self.T and self.availability[r][current_t]:
                streak = self.streaks[r][current_t]
                if streak > max_streak:
                    max_streak = streak
                    best_r = r

        if max_streak == 0:
            return ClusterType.ON_DEMAND
        else:
            if best_r != current_region and max_streak > current_streak:
                self.env.switch_region(best_r)
            return ClusterType.SPOT