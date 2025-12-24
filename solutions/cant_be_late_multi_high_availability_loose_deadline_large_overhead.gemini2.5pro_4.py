import json
import os
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "lookahead_optimizer"

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

        self.PANIC_THRESHOLD = 1.15
        W_hours = 8.0
        SWITCH_MARGIN_STEPS = 1.0

        self.W_steps = max(1, int(W_hours * 3600 / self.env.gap_seconds))
        self.SWITCH_MARGIN = (self.restart_overhead / self.env.gap_seconds) + SWITCH_MARGIN_STEPS

        self.availability: List[List[bool]] = []
        spec_dir = os.path.dirname(os.path.abspath(spec_path))
        for trace_file in config["trace_files"]:
            trace_path = os.path.join(spec_dir, trace_file)
            region_availability: List[bool] = []
            with open(trace_path) as f:
                for line in f:
                    region_availability.append(line.strip() == '1')
            self.availability.append(region_availability)

        if not self.availability:
            self.num_regions = 0
            self.trace_len = 0
            self.spot_counts = []
            return self

        self.num_regions = len(self.availability)
        self.trace_len = len(self.availability[0])

        self.spot_counts = [[0] * self.trace_len for _ in range(self.num_regions)]
        W = self.W_steps
        for r in range(self.num_regions):
            if self.trace_len == 0:
                continue

            W_clamped = min(W, self.trace_len)
            current_sum = sum(self.availability[r][0:W_clamped])
            if self.trace_len > 0:
                self.spot_counts[r][0] = current_sum
            
            for t in range(1, self.trace_len):
                lost_val = self.availability[r][t-1]
                gained_val = self.availability[r][t + W_clamped - 1] if (t + W_clamped - 1) < self.trace_len else False
                current_sum = current_sum - int(lost_val) + int(gained_val)
                self.spot_counts[r][t] = current_sum

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        current_step = int(current_time / self.env.gap_seconds)
        
        if self.trace_len > 0:
            current_step = min(current_step, self.trace_len - 1)

        remaining_work = self.task_duration - sum(self.task_done_time)

        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - current_time
        time_needed = remaining_work + self.remaining_restart_overhead
        if time_left <= time_needed * self.PANIC_THRESHOLD:
            return ClusterType.ON_DEMAND
        
        if not self.availability:
             return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        
        potentials = [self.spot_counts[r][current_step] for r in range(self.num_regions)]
        best_region = max(range(self.num_regions), key=potentials.__getitem__)
        best_potential = potentials[best_region]
        current_potential = potentials[current_region]

        should_switch = (current_region != best_region and 
                         best_potential > current_potential + self.SWITCH_MARGIN)
        
        if should_switch:
            self.env.switch_region(best_region)
            target_region = best_region
            effective_overhead = self.restart_overhead
        else:
            target_region = current_region
            effective_overhead = self.remaining_restart_overhead

        is_spot_available = self.availability[target_region][current_step]
        if is_spot_available:
            return ClusterType.SPOT
        else:
            next_spot_step = -1
            search_end = min(current_step + self.W_steps + 1, self.trace_len)
            for i in range(current_step + 1, search_end):
                if self.availability[target_region][i]:
                    next_spot_step = i
                    break
            
            if next_spot_step == -1:
                return ClusterType.ON_DEMAND
            
            wait_steps = next_spot_step - current_step
            wait_time = wait_steps * self.env.gap_seconds
            
            time_after_wait = current_time + wait_time
            time_left_after_wait = self.deadline - time_after_wait
            
            time_needed_after_wait = remaining_work + effective_overhead
            
            if time_left_after_wait <= time_needed_after_wait * self.PANIC_THRESHOLD:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
