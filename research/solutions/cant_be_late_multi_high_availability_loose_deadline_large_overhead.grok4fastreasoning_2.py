import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "greedy_spot"

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

        self.traces = []
        if "trace_files" in config:
            for tf in config["trace_files"]:
                with open(tf, 'r') as f:
                    self.traces.append(json.load(f))

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_step = int(elapsed // gap)

        if has_spot:
            return ClusterType.SPOT

        # Find best region with spot available now and longest streak
        max_streak = -1
        best_r = -1
        for r in range(num_regions):
            if current_step >= len(self.traces[r]):
                continue
            if not self.traces[r][current_step]:
                continue
            # Compute streak
            streak = 0
            s = current_step
            while s < len(self.traces[r]) and self.traces[r][s] and streak < 100:
                streak += 1
                s += 1
            if streak > max_streak:
                max_streak = streak
                best_r = r
            elif streak == max_streak and r < best_r:
                best_r = r

        if best_r != -1:
            self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND