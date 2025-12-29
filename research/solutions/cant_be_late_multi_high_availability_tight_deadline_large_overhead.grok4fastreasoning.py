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

        # Load traces
        self.traces = []
        for path in config["trace_files"]:
            with open(path, 'r') as f:
                trace = json.load(f)
                self.traces.append([bool(x) for x in trace])
        self.num_regions = len(self.traces)
        if self.num_regions > 0:
            self.T = len(self.traces[0])
        else:
            self.T = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_step = int(elapsed // gap)

        total_progress = sum(self.task_done_time)
        if total_progress >= self.task_duration:
            return ClusterType.NONE

        remaining_time = self.deadline - elapsed
        if remaining_time <= 0:
            return ClusterType.NONE

        if current_step >= self.T:
            return ClusterType.ON_DEMAND

        # Compute remaining steps approx
        remaining_steps_approx = int(remaining_time // gap) + 1

        # Find best region
        best_region = current_region
        best_score = -float('inf')
        switch_penalty = 1.0

        for r in range(self.num_regions):
            max_t = min(self.T, current_step + remaining_steps_approx)
            if max_t <= current_step:
                total_spot = 0
            else:
                total_spot = sum(1 for t in range(current_step, max_t) if self.traces[r][t])
            is_switch = 1 if r != current_region else 0
            score = total_spot - is_switch * switch_penalty
            if score > best_score:
                best_score = score
                best_region = r

        # Switch if better
        if best_region != current_region:
            self.env.switch_region(best_region)

        # Now check has_spot in new region
        new_region = self.env.get_current_region()  # should be best_region
        new_has_spot = False
        if current_step < self.T and new_region < self.num_regions and current_step < len(self.traces[new_region]):
            new_has_spot = self.traces[new_region][current_step]

        if new_has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND