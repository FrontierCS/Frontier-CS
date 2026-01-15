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
        # load availability
        self.availability = []
        for path in config["trace_files"]:
            with open(path, 'r') as tf:
                trace = json.load(tf)
                self.availability.append([bool(x) for x in trace])
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        if remaining_work <= 0:
            return ClusterType.NONE
        effective_elapsed = self.env.elapsed_seconds + self.remaining_restart_overhead
        remaining_time = self.deadline - effective_elapsed
        if remaining_time <= 0:
            return ClusterType.NONE
        current_r = self.env.get_current_region()
        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        num_regions = self.env.get_num_regions()
        gap = self.env.gap_seconds
        if has_spot:
            return ClusterType.SPOT
        # try to switch to a region with spot now
        best_r = -1
        best_streak = -1
        for r in range(num_regions):
            if r == current_r:
                continue
            if current_step >= len(self.availability[r]):
                continue
            if not self.availability[r][current_step]:
                continue
            # compute streak
            streak = 0
            max_streak_look = min(current_step + 10, len(self.availability[r]))
            for t in range(current_step, max_streak_look):
                if self.availability[r][t]:
                    streak += 1
                else:
                    break
            if streak > best_streak:
                best_streak = streak
                best_r = r
        if best_r != -1 and best_streak >= 1:
            self.env.switch_region(best_r)
            return ClusterType.SPOT
        # cannot get spot now
        # see if worth pausing for future spot
        min_wait_steps = float('inf')
        max_lookahead = 3
        for wait in range(1, max_lookahead + 1):
            k = current_step + wait
            has_spot_future = False
            for r in range(num_regions):
                if k < len(self.availability[r]) and self.availability[r][k]:
                    has_spot_future = True
                    break
            if has_spot_future:
                min_wait_steps = wait
                break
        if min_wait_steps != float('inf'):
            wait_time = min_wait_steps * gap
            buffer = self.restart_overhead + gap * 0.1
            if remaining_time > remaining_work + wait_time + buffer:
                return ClusterType.NONE
        # otherwise, use on-demand
        return ClusterType.ON_DEMAND