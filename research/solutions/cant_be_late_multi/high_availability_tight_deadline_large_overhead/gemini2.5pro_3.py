import json
from argparse import Namespace
import numpy as np

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                trace = [int(line.strip()) for line in f]
                self.spot_traces.append(trace)
        
        self.spot_traces = np.array(self.spot_traces, dtype=np.int8)

        self.num_regions = self.spot_traces.shape[0]
        self.max_trace_steps = self.spot_traces.shape[1]
        self.deadline_step_idx = int(self.deadline / self.env.gap_seconds)
        
        self.panic_buffer_factor = 2.0
        self.switch_gain_factor = 1.2
        self.wait_slack_factor = 0.5
        self.initial_slack = self.deadline - self.task_duration

        self.region_scores_cache = {}

        return self

    def _get_region_scores(self, current_time_step: int) -> np.ndarray:
        if current_time_step in self.region_scores_cache:
            return self.region_scores_cache[current_time_step]

        end_idx = min(self.deadline_step_idx, self.max_trace_steps)
        
        future_traces = self.spot_traces[:, current_time_step:end_idx]
        scores = np.sum(future_traces, axis=1)
        
        self.region_scores_cache[current_time_step] = scores
        return scores

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_time = self.env.elapsed_seconds
        remaining_work = self.task_duration - sum(self.task_done_time)

        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - current_time
        current_time_step = int(current_time / self.env.gap_seconds)
        
        if current_time_step >= self.max_trace_steps:
            current_time_step = self.max_trace_steps - 1

        time_needed_for_od = remaining_work + self.restart_overhead
        safety_buffer = self.panic_buffer_factor * self.restart_overhead

        if time_left <= time_needed_for_od + safety_buffer:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        region_scores = self._get_region_scores(current_time_step)
        best_region_idx = np.argmax(region_scores)
        
        chosen_region = current_region
        if best_region_idx != current_region:
            current_region_score = region_scores[current_region]
            best_region_score = region_scores[best_region_idx]
            
            gain_in_spot_steps = best_region_score - current_region_score
            gain_in_seconds = gain_in_spot_steps * self.env.gap_seconds
            
            switch_cost = self.restart_overhead
            
            if gain_in_seconds > switch_cost * self.switch_gain_factor:
                spot_available_at_target = self.spot_traces[best_region_idx, current_time_step] == 1
                if spot_available_at_target:
                    self.env.switch_region(best_region_idx)
                    chosen_region = best_region_idx

        spot_available_now = self.spot_traces[chosen_region, current_time_step] == 1
        if spot_available_now:
            return ClusterType.SPOT
        else:
            current_slack = time_left - remaining_work
            wait_threshold = self.initial_slack * self.wait_slack_factor
            
            future_spot_exists = region_scores[chosen_region] > 0

            if current_slack > wait_threshold and future_spot_exists:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND