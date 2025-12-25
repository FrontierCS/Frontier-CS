import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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

        # --- Custom Initialization and Pre-computation ---
        self.traces: List[List[int]] = []
        for trace_file in config["trace_files"]:
            try:
                with open(trace_file, 'r') as f:
                    trace = [int(line.strip()) for line in f if line.strip()]
                    self.traces.append(trace)
            except (IOError, ValueError):
                self.traces.append([])

        lookahead_window_hours = 3.0
        window_size = max(1, int(lookahead_window_hours * 3600.0 / self.gap_seconds))

        self.future_scores: List[List[float]] = []
        for trace in self.traces:
            if not trace:
                self.future_scores.append([])
                continue

            n = len(trace)
            cumsum = [0] * (n + 1)
            for i in range(n):
                cumsum[i + 1] = cumsum[i] + trace[i]

            scores = [0.0] * n
            for t in range(n):
                end_idx = min(t + window_size, n)
                window_len = end_idx - t
                current_sum = cumsum[end_idx] - cumsum[t]
                if window_len > 0:
                    scores[t] = float(current_sum) / window_len
            self.future_scores.append(scores)

        self.initial_slack = self.deadline - self.task_duration
        if self.initial_slack <= 0:
            self.initial_slack = 1.0

        self.SWITCH_IMPROVEMENT_THRESHOLD = 0.8
        self.OD_SLACK_THRESHOLD = 0.25

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        progress = sum(self.task_done_time)
        work_left = self.task_duration - progress

        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        critical_time_needed = work_left + self.gap_seconds + self.restart_overhead
        if time_left <= critical_time_needed:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        current_timestep = int(self.env.elapsed_seconds / self.gap_seconds)

        best_available_region = -1
        max_future_score = -1.0

        for r in range(self.env.get_num_regions()):
            if r < len(self.traces) and current_timestep < len(self.traces[r]) and self.traces[r][current_timestep] == 1:
                if r < len(self.future_scores) and current_timestep < len(self.future_scores[r]):
                    score = self.future_scores[r][current_timestep]
                    if score > max_future_score:
                        max_future_score = score
                        best_available_region = r

        if best_available_region == -1:
            slack_ratio = (time_left - work_left) / self.initial_slack
            if slack_ratio < self.OD_SLACK_THRESHOLD:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

        if has_spot:
            current_score = 0.0
            if current_region < len(self.future_scores) and current_timestep < len(self.future_scores[current_region]):
                 current_score = self.future_scores[current_region][current_timestep]

            if current_score >= max_future_score * self.SWITCH_IMPROVEMENT_THRESHOLD:
                return ClusterType.SPOT
            else:
                if best_available_region != current_region:
                    self.env.switch_region(best_available_region)
                return ClusterType.SPOT

        else:
            self.env.switch_region(best_available_region)
            return ClusterType.SPOT
