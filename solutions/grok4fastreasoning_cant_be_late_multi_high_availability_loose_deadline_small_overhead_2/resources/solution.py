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

        trace_files = config["trace_files"]
        self.num_regions = len(trace_files)
        self.traces: List[List[bool]] = []
        for tf in trace_files:
            with open(tf, 'r') as f:
                raw = json.load(f)
            trace = [x == 1 for x in raw] if raw else []
            self.traces.append(trace)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE

        t = self.env.elapsed_seconds // self.env.gap_seconds
        current_r = self.env.get_current_region()
        num_r = self.env.get_num_regions()

        target_r = -1
        # Prefer current region if spot available
        if t < len(self.traces[current_r]) and self.traces[current_r][t]:
            target_r = current_r
        else:
            # Find first other region with spot
            for r in range(num_r):
                if r != current_r and t < len(self.traces[r]) and self.traces[r][t]:
                    target_r = r
                    break

        if target_r != -1:
            if target_r != current_r:
                self.env.switch_region(target_r)
            return ClusterType.SPOT
        else:
            # No spot available anywhere, use ON_DEMAND
            return ClusterType.ON_DEMAND
