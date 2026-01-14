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
        self.observed = [0] * self.num_regions
        self.available_times = [0] * self.num_regions
        self.consecutive_searches = 0
        self.max_searches = self.num_regions * 2
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE

        remaining_work = self.task_duration - progress
        remaining_time = self.deadline - self.env.elapsed_seconds - self.remaining_restart_overhead
        if remaining_time <= 0:
            return ClusterType.NONE

        slack = remaining_time - remaining_work
        buffer = 2 * self.env.gap_seconds

        current = self.env.get_current_region()
        self.observed[current] += 1
        if has_spot:
            self.available_times[current] += 1

        if has_spot:
            self.consecutive_searches = 0
            return ClusterType.SPOT
        else:
            self.consecutive_searches += 1
            use_od = (slack < buffer) or (self.consecutive_searches > self.max_searches) or (remaining_work / remaining_time > 0.9)
            if use_od:
                self.consecutive_searches = 0
                return ClusterType.ON_DEMAND
            else:
                best_score = -1
                best_idx = -1
                for i in range(self.num_regions):
                    if i == current:
                        continue
                    if self.observed[i] == 0:
                        score = 0.5
                    else:
                        score = self.available_times[i] / self.observed[i]
                    if score > best_score:
                        best_score = score
                        best_idx = i
                if best_idx != -1:
                    self.env.switch_region(best_idx)
                return ClusterType.NONE