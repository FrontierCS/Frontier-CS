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

        self.traces = []
        for path in config["trace_files"]:
            with open(path, 'r') as tf:
                raw_trace = json.load(tf)
                trace = [bool(x) for x in raw_trace]
                self.traces.append(trace)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        t = int(self.env.elapsed_seconds // self.env.gap_seconds)
        num_r = self.env.get_num_regions()
        current = self.env.get_current_region()

        candidates = []
        for r in range(num_r):
            if t < len(self.traces[r]) and self.traces[r][t]:
                streak = 0
                for tt in range(t, len(self.traces[r])):
                    if self.traces[r][tt]:
                        streak += 1
                    else:
                        break
                dist = abs(r - current)
                candidates.append((streak, -dist, r))

        if candidates:
            candidates.sort(reverse=True)
            best_r = candidates[0][2]
            self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            future_candidates = []
            for r in range(num_r):
                streak = 0
                for tt in range(t + 1, len(self.traces[r])):
                    if self.traces[r][tt]:
                        streak += 1
                    else:
                        break
                dist = abs(r - current)
                future_candidates.append((streak, -dist, r))
            future_candidates.sort(reverse=True)
            best_r = future_candidates[0][2]
            self.env.switch_region(best_r)
            return ClusterType.ON_DEMAND