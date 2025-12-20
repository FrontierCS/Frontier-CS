import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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

        self.GAP_SECONDS = 3600.0

        self.trace_files = config['trace_files']
        self.num_regions = len(self.trace_files)
        
        num_steps = math.ceil(self.deadline / self.GAP_SECONDS) + 5

        self.spot_availability = []
        for trace_file in self.trace_files:
            region_availability = []
            try:
                with open(trace_file, 'r') as f:
                    lines = f.readlines()
                    for i in range(num_steps):
                        if i < len(lines):
                            available = bool(int(lines[i].strip()))
                            region_availability.append(available)
                        else:
                            region_availability.append(False)
            except (IOError, ValueError):
                region_availability = [False] * num_steps
            self.spot_availability.append(region_availability)

        self.spot_run_lengths = [[0] * num_steps for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            run = 0
            for step in range(num_steps - 1, -1, -1):
                if self.spot_availability[r][step]:
                    run += 1
                else:
                    run = 0
                self.spot_run_lengths[r][step] = run
        
        self.next_spot_step = [[num_steps] * num_steps for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            next_spot = num_steps
            for step in range(num_steps - 1, -1, -1):
                if self.spot_availability[r][step]:
                    next_spot = step
                if step < num_steps:
                    self.next_spot_step[r][step] = next_spot
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = max(0, self.task_duration - sum(self.task_done_time))
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        needed_overhead = 0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        time_if_od_completes = self.env.elapsed_seconds + needed_overhead + remaining_work
        
        if time_if_od_completes >= self.deadline:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        current_region = self.env.get_current_region()
        current_step = int(self.env.elapsed_seconds / self.GAP_SECONDS)
        slack = self.deadline - self.env.elapsed_seconds - remaining_work
        
        wait_time = float('inf')
        next_step_to_check = current_step + 1
        num_precomputed_steps = len(self.next_spot_step[0])
        
        if next_step_to_check < num_precomputed_steps:
            next_spot_start_step = self.next_spot_step[current_region][next_step_to_check]
            if next_spot_start_step < num_precomputed_steps:
                 wait_time = (next_spot_start_step - current_step) * self.GAP_SECONDS
        
        can_afford_wait = slack > wait_time

        step_after_switch = int((self.env.elapsed_seconds + self.restart_overhead) / self.GAP_SECONDS)
        best_switch_region = -1
        max_run_length = -1

        for r in range(self.num_regions):
            if r == current_region:
                continue
            if step_after_switch < num_precomputed_steps:
                run_length = self.spot_run_lengths[r][step_after_switch]
                if run_length > max_run_length:
                    max_run_length = run_length
                    best_switch_region = r
        
        can_afford_switch = slack > self.restart_overhead
        switch_is_promising = best_switch_region != -1 and max_run_length > 0
        
        time_to_spot_if_wait = self.env.elapsed_seconds + wait_time if can_afford_wait else float('inf')
        time_to_spot_if_switch = self.env.elapsed_seconds + self.restart_overhead if can_afford_switch and switch_is_promising else float('inf')

        if time_to_spot_if_wait <= time_to_spot_if_switch:
            return ClusterType.NONE
        elif time_to_spot_if_switch < float('inf'):
            self.env.switch_region(best_switch_region)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND
