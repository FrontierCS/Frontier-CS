import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CantBeLate"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self.spot_traces = []
        try:
            for trace_file in config["trace_files"]:
                with open(trace_file) as tf:
                    trace = [bool(int(line.strip())) for line in tf if line.strip()]
                    self.spot_traces.append(trace)
        except (IOError, ValueError):
            self.spot_traces = []

        if not self.spot_traces:
            self.num_regions = 0
            self.trace_len = 0
            self.future_streaks = []
            return self

        self.num_regions = len(self.spot_traces)
        self.trace_len = len(self.spot_traces[0]) if self.num_regions > 0 else 0

        self.future_streaks = [[0] * self.trace_len for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            for t in range(self.trace_len - 1, -1, -1):
                if self.spot_traces[r][t]:
                    if t == self.trace_len - 1:
                        self.future_streaks[r][t] = 1
                    else:
                        self.future_streaks[r][t] = 1 + self.future_streaks[r][t + 1]

        self.safety_margin_factor = 1.5

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed_time = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed_time

        safety_margin = self.safety_margin_factor * self.restart_overhead
        
        time_needed_guaranteed = remaining_work + self.remaining_restart_overhead
        
        if time_needed_guaranteed + safety_margin >= remaining_time:
            return ClusterType.ON_DEMAND

        if not self.spot_traces or self.num_regions == 0:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        current_step = int(elapsed_time // self.env.gap_seconds)
        
        if current_step >= self.trace_len:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        current_region = self.env.get_current_region()
        best_region_to_switch = -1
        max_streak = 0

        for r in range(self.num_regions):
            if r == current_region:
                continue
            
            streak = self.future_streaks[r][current_step]
            if streak > max_streak:
                max_streak = streak
                best_region_to_switch = r

        if best_region_to_switch != -1:
            self.env.switch_region(best_region_to_switch)
            return ClusterType.SPOT

        spot_coming_soon = False
        next_step = current_step + 1
        if next_step < self.trace_len:
            for r in range(self.num_regions):
                if self.spot_traces[r][next_step]:
                    spot_coming_soon = True
                    break
        
        slack = remaining_time - (time_needed_guaranteed + safety_margin)
        
        if spot_coming_soon and slack > self.env.gap_seconds:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND