import json
import gzip
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that dynamically chooses between SPOT,
    ON_DEMAND, and NONE based on the remaining time to deadline (slack). It
    pre-processes spot availability traces to make informed decisions about
    switching regions or waiting for spot availability.
    """

    NAME = "cant-be-late-heuristic"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the solution by loading the problem specification and
        pre-processing the spot availability traces for all regions.
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

        self._preprocess_traces(config["trace_files"])

        self.high_slack_threshold = 0.5
        self.low_slack_threshold = 0.15

        return self

    def _preprocess_traces(self, trace_files: list[str]):
        """
        Loads and parses trace files to create data structures for quick lookups.
        It computes spot availability streaks and the next available spot time
        for each time step in each region.
        """
        num_regions = len(trace_files)
        self.num_timesteps = int(self.deadline / self.env.gap_seconds) + 5

        self.spot_traces = [[False] * self.num_timesteps for _ in range(num_regions)]

        for r, trace_file in enumerate(trace_files):
            try:
                with gzip.open(trace_file, 'rt', encoding='utf-8') as f:
                    trace_data = json.load(f)
            except (gzip.BadGzipFile, FileNotFoundError, IsADirectoryError):
                 with open(trace_file, 'r') as f:
                    trace_data = json.load(f)

            for entry in trace_data:
                time_sec = float(entry["time"])
                spot_available = bool(entry["spot"])
                k = int(time_sec / self.env.gap_seconds)
                if k < self.num_timesteps:
                    self.spot_traces[r][k] = spot_available

        self.spot_streaks = [[0] * self.num_timesteps for _ in range(num_regions)]
        self.next_spot_start = [[self.num_timesteps] * self.num_timesteps for _ in range(num_regions)]

        for r in range(num_regions):
            if self.num_timesteps > 0 and self.spot_traces[r][self.num_timesteps - 1]:
                self.spot_streaks[r][self.num_timesteps - 1] = 1

            for k in range(self.num_timesteps - 2, -1, -1):
                if self.spot_traces[r][k]:
                    self.spot_streaks[r][k] = 1 + self.spot_streaks[r][k + 1]

            last_seen_spot = self.num_timesteps
            for k in range(self.num_timesteps - 1, -1, -1):
                if self.spot_traces[r][k]:
                    last_seen_spot = k
                self.next_spot_start[r][k] = last_seen_spot

    def _find_best_switch_target(self, k: int) -> tuple[int, int]:
        """
        Finds the best region to switch to, based on the longest available
        spot streak at the current time step `k`.
        """
        best_region = -1
        max_streak = 0
        current_region = self.env.get_current_region()
        for r in range(self.env.get_num_regions()):
            if r == current_region:
                continue
            
            streak = self.spot_streaks[r][k] if k < self.num_timesteps else 0
            if streak > max_streak:
                max_streak = streak
                best_region = r
        return best_region, max_streak

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Core decision-making logic, executed at each time step.
        """
        progress = sum(self.task_done_time)
        if progress >= self.task_duration:
            return ClusterType.NONE

        remaining_work = self.task_duration - progress
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        base_slack = time_to_deadline - remaining_work
        effective_slack = base_slack - self.remaining_restart_overhead

        if effective_slack <= self.restart_overhead:
             return ClusterType.ON_DEMAND

        k = int(self.env.elapsed_seconds / self.env.gap_seconds)
        current_region = self.env.get_current_region()
        
        slack_ratio = effective_slack / remaining_work if remaining_work > 0 else float('inf')

        # Policy 1: High Slack -> Aggressively seek SPOT
        if slack_ratio > self.high_slack_threshold:
            if has_spot:
                return ClusterType.SPOT
            
            best_region, _ = self._find_best_switch_target(k)
            if best_region != -1:
                self.env.switch_region(best_region)
                return ClusterType.SPOT
            
            return ClusterType.NONE

        # Policy 2: Medium Slack -> Cautiously seek SPOT
        if slack_ratio > self.low_slack_threshold:
            if has_spot:
                return ClusterType.SPOT

            best_region, _ = self._find_best_switch_target(k)
            if best_region != -1:
                next_spot_k_current = self.next_spot_start[current_region][k] if k < self.num_timesteps else self.num_timesteps
                
                if next_spot_k_current >= self.num_timesteps:
                    if effective_slack > self.restart_overhead * 2:
                        self.env.switch_region(best_region)
                        return ClusterType.SPOT
                else:
                    wait_time_cost = (next_spot_k_current - k) * self.env.gap_seconds
                    switch_time_cost = self.restart_overhead
                    if switch_time_cost < wait_time_cost and effective_slack > switch_time_cost + self.restart_overhead:
                        self.env.switch_region(best_region)
                        return ClusterType.SPOT

            return ClusterType.ON_DEMAND
            
        # Policy 3: Low Slack -> Use ON_DEMAND for safety
        else:
            return ClusterType.ON_DEMAND