import json
from argparse import Namespace
import sys

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that aims to minimize cost while guaranteeing
    completion before the deadline.
    """

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        This involves loading the config, initializing the parent strategy,
        and pre-processing spot availability traces for all regions.
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

        self.traces = []
        self.prefix_sums = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                trace = [int(line.strip()) for line in f]
                self.traces.append(trace)
                
                sums = [0] * (len(trace) + 1)
                for i in range(len(trace)):
                    sums[i+1] = sums[i] + trace[i]
                self.prefix_sums.append(sums)

        return self

    def _get_future_spot_score(self, region_idx: int, start_step: int, window_steps: int) -> int:
        """
        Calculates the number of available spot steps in a future window for a given region.
        Uses the pre-computed prefix sums for O(1) calculation.
        """
        if region_idx >= len(self.traces):
            return 0
            
        trace_len = len(self.traces[region_idx])
        if start_step >= trace_len:
            return 0
        
        end_step = min(trace_len - 1, start_step + window_steps - 1)
        
        score = self.prefix_sums[region_idx][end_step + 1] - self.prefix_sums[region_idx][start_step]
        return score

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        
        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        
        on_demand_finish_duration = work_left + self.restart_overhead
        
        safety_buffer = self.env.gap_seconds

        if on_demand_finish_duration >= time_left - safety_buffer:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        
        if has_spot:
            return ClusterType.SPOT

        current_step_idx = int(self.env.elapsed_seconds / self.env.gap_seconds) if self.env.gap_seconds > 0 else 0
        
        best_region_idx = -1
        max_score = -1
        
        lookahead_duration = min(work_left, 24 * 3600)
        lookahead_steps = int(lookahead_duration / self.env.gap_seconds) if self.env.gap_seconds > 0 else 0

        can_switch_profitably = self.env.gap_seconds > self.restart_overhead

        if can_switch_profitably:
            num_regions = self.env.get_num_regions()
            for r in range(num_regions):
                if r == current_region:
                    continue

                if r < len(self.traces) and current_step_idx < len(self.traces[r]) and self.traces[r][current_step_idx]:
                    score = self._get_future_spot_score(r, current_step_idx, lookahead_steps)
                    if score > max_score:
                        max_score = score
                        best_region_idx = r
        
        if best_region_idx != -1:
            self.env.switch_region(best_region_idx)
            return ClusterType.SPOT
            
        slack = time_left - on_demand_finish_duration
        if slack > self.env.gap_seconds:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND