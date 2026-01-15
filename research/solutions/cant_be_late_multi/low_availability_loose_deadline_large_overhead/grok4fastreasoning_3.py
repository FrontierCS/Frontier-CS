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

        # Load availability traces
        self.availability = []
        self.num_regions = len(config["trace_files"])
        for path in config["trace_files"]:
            with open(path, 'r') as f:
                data = json.load(f)
                self.availability.append([bool(x) for x in data])

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        if gap == 0:
            gap = 1.0
        current_step = int(current_time // gap)

        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - current_time
        if time_left <= 0:
            return ClusterType.NONE

        # Prefer SPOT in current region if available
        if current_step < len(self.availability[current_region]) and self.availability[current_region][current_step]:
            return ClusterType.SPOT

        # Find best region with SPOT available now, preferring longest future availability
        best_region = None
        best_future = -1
        for r in range(self.num_regions):
            if current_step < len(self.availability[r]) and self.availability[r][current_step]:
                # Compute consecutive future spots (look ahead up to 10 steps)
                future = 0
                max_lookahead = min(current_step + 10, len(self.availability[r]))
                for s in range(current_step, max_lookahead):
                    if self.availability[r][s]:
                        future += 1
                    else:
                        break
                if future > best_future:
                    best_future = future
                    best_region = r

        # If found a better region, switch and use SPOT
        if best_region is not None and best_region != current_region:
            self.env.switch_region(best_region)
            return ClusterType.SPOT

        # Fall back to ON_DEMAND in current region
        return ClusterType.ON_DEMAND