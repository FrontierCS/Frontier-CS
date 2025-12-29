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
        trace_files = config.get("trace_files", [])
        for path in trace_files:
            with open(path, 'r') as f:
                trace_data = json.load(f)
            trace = [bool(x) for x in trace_data]
            self.traces.append(trace)
        self.num_regions = len(self.traces)
        self.num_steps = len(self.traces[0]) if self.num_regions > 0 else 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, 'traces') or self.num_regions == 0:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_step = int(elapsed // gap)

        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        remaining_time = self.deadline - elapsed

        if remaining_work <= 0 or elapsed >= self.deadline:
            return ClusterType.NONE

        # Safety check: if tight on time, use ON_DEMAND without switching
        pending_overhead = getattr(self, 'remaining_restart_overhead', 0.0)
        if remaining_time < remaining_work + pending_overhead + self.restart_overhead:
            return ClusterType.ON_DEMAND

        # Compute current streak if available
        current_streak = 0
        if (current_step < len(self.traces[current_region]) and
            self.traces[current_region][current_step]):
            t = current_step
            while (t < len(self.traces[current_region]) and
                   self.traces[current_region][t]):
                current_streak += 1
                t += 1

        # Find best region
        max_streak = current_streak
        best_r = current_region if current_streak > 0 else -1
        for r in range(self.num_regions):
            if r == current_region:
                continue
            if current_step >= len(self.traces[r]) or not self.traces[r][current_step]:
                continue
            streak = 0
            t = current_step
            while t < len(self.traces[r]) and self.traces[r][t]:
                streak += 1
                t += 1
            if streak > max_streak:
                max_streak = streak
                best_r = r

        if max_streak == 0:
            return ClusterType.ON_DEMAND

        # Switch if necessary
        if best_r != current_region:
            self.env.switch_region(best_r)

        return ClusterType.SPOT