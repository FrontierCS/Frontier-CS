import json
from argparse import Namespace
import sys

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "predictive_slack_manager"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution and pre-process trace data."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self.spot_availability_traces = []
        if 'trace_files' in config:
            for trace_file in config['trace_files']:
                with open(trace_file) as f:
                    self.spot_availability_traces.append(json.load(f))
        
        if not self.spot_availability_traces or not self.spot_availability_traces[0]:
            self.num_regions = 0
            self.num_steps = 0
            return self

        self.num_regions = len(self.spot_availability_traces)
        self.num_steps = min(len(trace) for trace in self.spot_availability_traces) if self.num_regions > 0 else 0

        self.next_spot_availability = [[self.num_steps] * self.num_steps for _ in range(self.num_regions)]
        self.consecutive_spot = [[0] * (self.num_steps + 1) for _ in range(self.num_regions)]
        
        for r in range(self.num_regions):
            trace = self.spot_availability_traces[r]
            
            last_seen_spot = self.num_steps
            for s in range(self.num_steps - 1, -1, -1):
                if s < len(trace) and trace[s]:
                    last_seen_spot = s
                self.next_spot_availability[r][s] = last_seen_spot
            
            for s in range(self.num_steps - 1, -1, -1):
                if s < len(trace) and trace[s]:
                    self.consecutive_spot[r][s] = 1 + self.consecutive_spot[r][s + 1]
                else:
                    self.consecutive_spot[r][s] = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decide next action based on current state."""
        remaining_work = self.task_duration - sum(self.task_done_time)

        if remaining_work <= 0:
            return ClusterType.NONE

        if has_spot:
            return ClusterType.SPOT

        current_time = self.env.elapsed_seconds
        slack_time = self.deadline - (current_time + remaining_work)

        if slack_time <= 0:
            return ClusterType.ON_DEMAND
            
        current_step = int(current_time / self.env.gap_seconds)
        
        if current_step >= self.num_steps:
            return ClusterType.ON_DEMAND

        if slack_time >= self.restart_overhead:
            candidates = {}
            for r in range(self.num_regions):
                if self.spot_availability_traces[r][current_step]:
                    candidates[r] = self.consecutive_spot[r][current_step]
            
            if candidates:
                best_region, streak = max(candidates.items(), key=lambda item: item[1])
                expected_spot_time = streak * self.env.gap_seconds
                
                if expected_spot_time > self.restart_overhead:
                    self.env.switch_region(best_region)
                    return ClusterType.SPOT

        current_region = self.env.get_current_region()
        min_time_cost_to_wait = float('inf')
        
        for r in range(self.num_regions):
            if current_step < self.num_steps:
                next_step = self.next_spot_availability[r][current_step]
                if next_step < self.num_steps:
                    wait_time = (next_step - current_step) * self.env.gap_seconds
                    switch_overhead = self.restart_overhead if r != current_region else 0.0
                    total_time_cost = wait_time + switch_overhead
                    if total_time_cost < min_time_cost_to_wait:
                        min_time_cost_to_wait = total_time_cost

        if slack_time >= min_time_cost_to_wait:
            return ClusterType.NONE
        
        return ClusterType.ON_DEMAND
