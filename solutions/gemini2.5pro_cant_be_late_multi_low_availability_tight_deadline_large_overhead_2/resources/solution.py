import json
from argparse import Namespace
import numpy as np

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    Your multi-region scheduling strategy.
    """

    NAME = "AdaptiveSlackStrategy"

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

        self.trace_files = config.get("trace_files", [])
        self.spot_availability = []
        for trace_file in self.trace_files:
            try:
                with open(trace_file, 'r') as f:
                    content = f.read().split()
                    self.spot_availability.append([bool(int(x)) for x in content])
            except (IOError, ValueError):
                pass
        
        self.max_trace_len = 0
        if self.spot_availability:
            self.max_trace_len = max(len(trace) for trace in self.spot_availability) if self.spot_availability else 0

        for trace in self.spot_availability:
            if len(trace) < self.max_trace_len:
                trace.extend([False] * (self.max_trace_len - len(trace)))
        
        self.num_regions_with_traces = len(self.spot_availability)
        
        self.forward_spot_streak = np.zeros((self.num_regions_with_traces, self.max_trace_len), dtype=int)
        if self.num_regions_with_traces > 0 and self.max_trace_len > 0:
            for r in range(self.num_regions_with_traces):
                if self.spot_availability[r][self.max_trace_len - 1]:
                    self.forward_spot_streak[r, self.max_trace_len - 1] = 1
                for t in range(self.max_trace_len - 2, -1, -1):
                    if self.spot_availability[r][t]:
                        self.forward_spot_streak[r, t] = self.forward_spot_streak[r, t + 1] + 1

        self.initial_slack = self.deadline - self.task_duration
        self.critical_overhead_multiplier = 1.1 
        self.switch_overhead_multiplier = 1.1
        self.caution_slack_fraction = 0.35

        return self

    def _get_spot_streak(self, region_idx: int, step_idx: int) -> int:
        if 0 <= region_idx < self.num_regions_with_traces and 0 <= step_idx < self.max_trace_len:
            return self.forward_spot_streak[region_idx, step_idx]
        return 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        
        current_step = 0
        if self.env.gap_seconds > 0:
            current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        
        critical_threshold = work_left + self.restart_overhead * self.critical_overhead_multiplier + self.env.gap_seconds
        if time_left <= critical_threshold:
            return ClusterType.ON_DEMAND

        best_region_idx = -1
        max_streak = 0
        num_regions = self.env.get_num_regions()
        
        for r_idx in range(num_regions):
            streak = self._get_spot_streak(r_idx, current_step)
            if streak > max_streak:
                max_streak = streak
                best_region_idx = r_idx

        if has_spot:
            return ClusterType.SPOT

        switch_threshold_seconds = self.restart_overhead * self.switch_overhead_multiplier
        if best_region_idx != -1 and max_streak * self.env.gap_seconds > switch_threshold_seconds:
            current_region_idx = self.env.get_current_region()
            if current_region_idx != best_region_idx:
                self.env.switch_region(best_region_idx)
            return ClusterType.SPOT
            
        current_slack = time_left - work_left
        caution_threshold_slack = self.initial_slack * self.caution_slack_fraction
        
        if current_slack <= caution_threshold_slack:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE
