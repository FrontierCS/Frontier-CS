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
        self.num_regions = self.env.get_num_regions()
        self.availability = []
        trace_files = config["trace_files"]
        for path in trace_files:
            with open(path, 'r') as f:
                data = json.load(f)
                self.availability.append([bool(x) for x in data])
        gap = self.env.gap_seconds
        max_steps = int(self.deadline / gap) + 100 if gap > 0 else 0
        self.streaks = [[0] * max_steps for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            avail = self.availability[r]
            for t in range(max_steps - 1, -1, -1):
                if t >= len(avail) or not avail[t]:
                    self.streaks[r][t] = 0
                else:
                    ns = self.streaks[r][t + 1] if t + 1 < max_steps else 0
                    self.streaks[r][t] = 1 + ns
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE
        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        current_region = self.env.get_current_region()
        candidates = []
        if has_spot:
            candidates.append(current_region)
        for r in range(self.num_regions):
            if r != current_region and current_step < len(self.availability[r]) and self.availability[r][current_step]:
                candidates.append(r)
        if candidates:
            if has_spot:
                return ClusterType.SPOT
            else:
                best_r = max(candidates, key=lambda rr: self.streaks[rr][current_step])
                self.env.switch_region(best_r)
                return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND