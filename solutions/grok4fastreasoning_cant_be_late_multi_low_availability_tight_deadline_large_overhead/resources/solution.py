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

        self.availability = []
        for tf in config.get("trace_files", []):
            with open(tf, 'r') as f:
                trace = json.load(f)
            self.availability.append([bool(x) for x in trace])

        if self.availability:
            spot_counts = [sum(trace) for trace in self.availability]
            self.best_region = spot_counts.index(max(spot_counts))
        else:
            self.best_region = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_t = int(self.env.elapsed_seconds // self.env.gap_seconds)
        current_r = self.env.get_current_region()
        if current_r != self.best_region:
            self.env.switch_region(self.best_region)
            current_r = self.best_region
            avail = self.availability[current_r][current_t] if current_t < len(self.availability[current_r]) else False
        else:
            avail = has_spot
        if avail:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND
