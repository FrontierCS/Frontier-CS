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
        self.traces: List[List] = []
        trace_files = config.get("trace_files", [])
        self.num_regions = len(trace_files)
        for path in trace_files:
            with open(path, 'r') as tf:
                trace = json.load(tf)
                self.traces.append(trace)
        self.T = len(self.traces[0]) if self.traces else 0

        # Precompute streaks
        self.streaks = [[0] * self.T for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            for t in range(self.T - 1, -1, -1):
                if bool(self.traces[r][t]):
                    self.streaks[r][t] = 1 + (self.streaks[r][t + 1] if t + 1 < self.T else 0)
                else:
                    self.streaks[r][t] = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_step = int(elapsed // gap)
        if current_step >= self.T:
            return ClusterType.ON_DEMAND

        use_spot = False
        target_region = current_region
        if has_spot:
            use_spot = True
        else:
            # Find best region with spot now
            best_streak = -1
            best_r = -1
            for r in range(self.num_regions):
                if bool(self.traces[r][current_step]):
                    streak = self.streaks[r][current_step]
                    if streak > best_streak:
                        best_streak = streak
                        best_r = r
            if best_r != -1:
                target_region = best_r
                use_spot = True

        if use_spot:
            if target_region != current_region:
                self.env.switch_region(target_region)
            return ClusterType.SPOT
        else:
            # No spot anywhere, use ON_DEMAND, stay
            return ClusterType.ON_DEMAND