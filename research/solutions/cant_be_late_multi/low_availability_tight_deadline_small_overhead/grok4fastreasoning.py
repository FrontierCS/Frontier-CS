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

        # Load availability traces
        trace_files = config.get("trace_files", [])
        self.availability: List[List[bool]] = []
        for path in trace_files:
            with open(path, 'r') as f:
                content = f.read()
            try:
                trace = json.loads(content)
            except json.JSONDecodeError:
                trace = [line.strip() for line in content.splitlines() if line.strip()]
                trace = [bool(int(x)) for x in trace]
            else:
                trace = [bool(x) for x in trace]
            self.availability.append(trace)

        # Initialize progress tracking
        self._progress = 0.0
        self._prev_num_segments = 0
        self._initialized = False

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._progress = sum(self.task_done_time)
            self._prev_num_segments = len(self.task_done_time)
            self._initialized = True

        current_num = len(self.task_done_time)
        if current_num > self._prev_num_segments:
            new_segments = current_num - self._prev_num_segments
            self._progress += sum(self.task_done_time[-new_segments:])
            self._prev_num_segments = current_num

        if self._progress >= self.task_duration:
            return ClusterType.NONE

        current_r = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        gap = self.env.gap_seconds
        current_t = int(self.env.elapsed_seconds // gap)

        # Check if current has spot
        use_spot = False
        target_r = current_r
        if len(self.availability) > 0 and current_t < len(self.availability[0]):
            if self.availability[current_r][current_t]:
                use_spot = True
            else:
                # Find smallest r with spot
                for r in range(num_regions):
                    if self.availability[r][current_t]:
                        target_r = r
                        use_spot = True
                        break

        if use_spot:
            if target_r != current_r:
                self.env.switch_region(target_r)
            return ClusterType.SPOT
        else:
            # No spot available anywhere, use on-demand
            return ClusterType.ON_DEMAND