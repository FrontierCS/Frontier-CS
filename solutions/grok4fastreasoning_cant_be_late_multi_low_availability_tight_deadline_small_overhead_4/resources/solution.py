import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "greedy_spot_multi"

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

        self.num_regions = len(config["trace_files"])
        self.availability = []
        for trace_path in config["trace_files"]:
            with open(trace_path, 'r') as f:
                data = json.load(f)
                avail = data.get("availability", data)
                self.availability.append([bool(x) for x in avail])

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        pending_overhead = self.remaining_restart_overhead
        slack = remaining_time - pending_overhead - remaining_work
        if slack < 2 * self.restart_overhead:
            return ClusterType.ON_DEMAND

        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        current_region = self.env.get_current_region()
        target_region = None
        for r in range(self.num_regions):
            if current_step < len(self.availability[r]) and self.availability[r][current_step]:
                target_region = r
                break
        if target_region is not None:
            if target_region != current_region:
                self.env.switch_region(target_region)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND
