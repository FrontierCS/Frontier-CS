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

        self.availabilities: List[List[bool]] = []
        for path in config["trace_files"]:
            with open(path, 'r') as tf:
                data = json.load(tf)
                if isinstance(data, dict) and "availability" in data:
                    avail = data["availability"]
                else:
                    avail = data
                self.availabilities.append([bool(x) for x in avail])
        self.num_regions = len(self.availabilities)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if has_spot:
            return ClusterType.SPOT

        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_hour = int(elapsed // 3600)
        num_regions = self.env.get_num_regions()

        best_region = -1
        best_streak = -1
        look_ahead = 24

        for r in range(num_regions):
            if current_hour >= len(self.availabilities[r]):
                continue
            if not self.availabilities[r][current_hour]:
                continue
            streak = 0
            max_t = min(current_hour + look_ahead, len(self.availabilities[r]))
            for t in range(current_hour, max_t):
                if self.availabilities[r][t]:
                    streak += 1
                else:
                    break
            if streak > best_streak:
                best_streak = streak
                best_region = r

        if best_region != -1:
            self.env.switch_region(best_region)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND