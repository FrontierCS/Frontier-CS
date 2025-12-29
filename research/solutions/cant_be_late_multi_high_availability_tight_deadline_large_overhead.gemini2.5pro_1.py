import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "OfflineLookahead"

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

        self.traces = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as tf:
                trace_data = json.load(tf)
                self.traces.append(trace_data)

        if not self.traces:
            self.num_regions = 0
            self.num_timesteps = 0
            self.run_lengths = []
        else:
            self.num_regions = len(self.traces)
            self.num_timesteps = len(self.traces[0]) if self.num_regions > 0 else 0

            self.run_lengths = [[0] * self.num_timesteps for _ in range(self.num_regions)]
            for r in range(self.num_regions):
                count = 0
                for t in range(self.num_timesteps - 1, -1, -1):
                    if self.traces[r][t]:
                        count += 1
                    else:
                        count = 0
                    self.run_lengths[r][t] = count
        
        self.gap_seconds = None

        self.SLACK_THRESHOLD_FACTOR = 2.0
        self.SWITCH_THRESHOLD_FACTOR = 1.5

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.gap_seconds is None:
            self.gap_seconds = self.env.gap_seconds
            if self.gap_seconds == 0:
                self.gap_seconds = 3600.0

        work_done = sum(self.task_done_time)
        work_to_do = self.task_duration - work_done

        if work_to_do <= 0:
            return ClusterType.NONE

        if self.num_regions == 0:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        elapsed_seconds = self.env.elapsed_seconds
        timestep = int(elapsed_seconds / self.gap_seconds)
        
        safe_timestep = min(timestep, self.num_timesteps - 1)

        current_region = self.env.get_current_region()
        best_alt_run = 0
        best_alt_region = -1

        for r in range(self.num_regions):
            if r == current_region:
                continue
            
            run_at_r = self.run_lengths[r][safe_timestep]
            if run_at_r > best_alt_run:
                best_alt_run = run_at_r
                best_alt_region = r
        
        switch_overhead_steps = self.restart_overhead / self.gap_seconds
        if best_alt_region != -1 and best_alt_run > switch_overhead_steps * self.SWITCH_THRESHOLD_FACTOR:
            self.env.switch_region(best_alt_region)
            return ClusterType.SPOT

        time_to_deadline = self.deadline - elapsed_seconds
        od_time_needed = work_to_do + self.remaining_restart_overhead
        slack = time_to_deadline - od_time_needed

        slack_threshold = self.restart_overhead * self.SLACK_THRESHOLD_FACTOR

        if slack > slack_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND