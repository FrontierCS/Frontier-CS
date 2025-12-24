import json
from argparse import Namespace
import os

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

        self.spec_dir = os.path.dirname(spec_path)
        self.trace_files = config.get("trace_files", [])

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        return self

    def _lazy_init(self):
        """
        Parses trace files on the first call to _step, once the environment
        is available.
        """
        self.initialized = True
        self.gap_seconds = self.env.gap_seconds
        self.num_regions = self.env.get_num_regions()
        
        self.availability = []
        if self.trace_files:
            for trace_file in self.trace_files:
                region_trace = []
                full_trace_path = os.path.join(self.spec_dir, trace_file)
                try:
                    with open(full_trace_path, 'r') as f:
                        for line in f:
                            region_trace.append(line.strip() == '1')
                except FileNotFoundError:
                    pass
                self.availability.append(region_trace)
        
        if self.availability and any(self.availability):
            max_len = 0
            for t in self.availability:
                if t:
                    max_len = max(max_len, len(t))
            
            for trace in self.availability:
                if trace:
                    trace.extend([False] * (max_len - len(trace)))
            self.total_timesteps = max_len
        else:
            self.availability = [[False] * 1 for _ in range(self.num_regions)]
            self.total_timesteps = 1

        # Strategy Tuning Parameters
        self.switch_slack_factor = 2.0 
        self.lookahead_hours = 12.0
        self.wait_threshold_factor = 0.5 
        self.switch_improvement_hours = 2.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, 'initialized'):
            self._lazy_init()

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_available = self.deadline - time_elapsed
        
        critical_path_duration = work_remaining + self.remaining_restart_overhead
        
        if critical_path_duration >= time_available:
            return ClusterType.ON_DEMAND

        slack = time_available - critical_path_duration
        
        safety_margin = self.restart_overhead + self.gap_seconds
        
        if slack < safety_margin:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        
        if has_spot:
            return ClusterType.SPOT

        if slack < self.restart_overhead * self.switch_slack_factor:
            return ClusterType.ON_DEMAND
        
        current_timestep = 0
        if self.gap_seconds > 0:
            current_timestep = min(self.total_timesteps - 1, int(time_elapsed / self.gap_seconds))

        lookahead_steps = 0
        if self.gap_seconds > 0:
            lookahead_steps = int(self.lookahead_hours * 3600 / self.gap_seconds)
        
        best_switch_region = -1
        best_score = -1
        
        for r in range(self.num_regions):
            if r != current_region:
                if len(self.availability[r]) > current_timestep and self.availability[r][current_timestep]:
                    end_ts = min(self.total_timesteps, current_timestep + lookahead_steps)
                    score = sum(self.availability[r][current_timestep:end_ts])
                    if score > best_score:
                        best_score = score
                        best_switch_region = r
        
        current_score = 0
        if len(self.availability[current_region]) > current_timestep:
            end_ts = min(self.total_timesteps, current_timestep + lookahead_steps)
            current_score = sum(self.availability[current_region][current_timestep:end_ts])
        
        switch_improvement_steps = 0
        if self.gap_seconds > 0:
            switch_improvement_steps = self.switch_improvement_hours * 3600 / self.gap_seconds

        if best_switch_region != -1 and best_score > current_score + switch_improvement_steps:
            self.env.switch_region(best_switch_region)
            return ClusterType.SPOT
            
        if current_score > self.wait_threshold_factor * lookahead_steps:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
