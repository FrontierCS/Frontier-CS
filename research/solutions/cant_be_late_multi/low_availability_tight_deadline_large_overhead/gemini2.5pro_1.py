import json
from argparse import Namespace
import math
import sys

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CantBeLate_v4"

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

        self.spot_availability_traces = []
        if "trace_files" in config:
            for trace_file in config["trace_files"]:
                with open(trace_file) as f:
                    self.spot_availability_traces.append(
                        [bool(int(line.strip())) for line in f if line.strip()]
                    )

        if not self.spot_availability_traces:
            return self

        self.num_trace_steps = len(self.spot_availability_traces[0])
        
        self.spot_prefix_sums = []
        for trace in self.spot_availability_traces:
            prefix_sum = [0] * (self.num_trace_steps + 1)
            current_sum = 0
            for i in range(self.num_trace_steps):
                current_sum += trace[i]
                prefix_sum[i + 1] = current_sum
            self.spot_prefix_sums.append(prefix_sum)

        self.next_spot_steps = []
        for trace in self.spot_availability_traces:
            next_spot = [self.num_trace_steps] * self.num_trace_steps
            last_seen_spot = self.num_trace_steps
            for i in range(self.num_trace_steps - 1, -1, -1):
                if trace[i]:
                    last_seen_spot = i
                next_spot[i] = last_seen_spot
            self.next_spot_steps.append(next_spot)

        self.PRICE_ON_DEMAND = 3.06
        self.PRICE_SPOT = 0.9701
        
        overhead_hours = self.restart_overhead / 3600.0
        price_diff = self.PRICE_ON_DEMAND - self.PRICE_SPOT
        if price_diff > 1e-9:
             self.BREAK_EVEN_SPOT_HOURS_GAIN = (overhead_hours * self.PRICE_ON_DEMAND) / price_diff
        else:
             self.BREAK_EVEN_SPOT_HOURS_GAIN = float('inf')

        self.LOOKAHEAD_STEPS = int(4 * 3600 / self.env.gap_seconds)
        self.SAFETY_BUFFER = self.restart_overhead

        return self

    def _get_region_quality(self, region_idx: int, start_step: int, num_steps: int) -> int:
        if start_step >= self.num_trace_steps:
            return 0
        end_step = min(start_step + num_steps, self.num_trace_steps)
        return self.spot_prefix_sums[region_idx][end_step] - self.spot_prefix_sums[region_idx][start_step]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, 'spot_availability_traces') or not self.spot_availability_traces:
             return ClusterType.ON_DEMAND if not has_spot else ClusterType.SPOT

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        if current_step >= self.num_trace_steps:
             return ClusterType.ON_DEMAND

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        time_needed_on_demand = remaining_work + self.remaining_restart_overhead
        
        if time_to_deadline <= time_needed_on_demand + self.SAFETY_BUFFER:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        if num_regions > 1:
            qualities = [self._get_region_quality(j, current_step, self.LOOKAHEAD_STEPS) for j in range(num_regions)]
            
            best_region_idx = qualities.index(max(qualities))

            if best_region_idx != current_region:
                current_quality = qualities[current_region]
                best_quality = qualities[best_region_idx]
                
                actual_spot_steps_gain = best_quality - current_quality
                actual_spot_hours_gain = actual_spot_steps_gain * self.env.gap_seconds / 3600.0

                slack = time_to_deadline - time_needed_on_demand

                if (actual_spot_hours_gain > self.BREAK_EVEN_SPOT_HOURS_GAIN and
                    slack > self.restart_overhead + self.SAFETY_BUFFER):
                    
                    self.env.switch_region(best_region_idx)
                    current_region = best_region_idx
                    has_spot = self.spot_availability_traces[current_region][current_step]

        if has_spot:
            return ClusterType.SPOT
        else:
            next_spot_avail_step = self.next_spot_steps[current_region][current_step]
            
            if next_spot_avail_step >= self.num_trace_steps:
                return ClusterType.ON_DEMAND

            wait_steps = next_spot_avail_step - current_step
            wait_time = wait_steps * self.env.gap_seconds
            
            slack = time_to_deadline - time_needed_on_demand
            
            if slack > wait_time + self.SAFETY_BUFFER:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND