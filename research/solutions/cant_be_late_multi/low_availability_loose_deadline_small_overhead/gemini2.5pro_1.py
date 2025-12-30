import json
import math
import os
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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
        spec_dir = os.path.dirname(spec_path)
        for trace_file in config["trace_files"]:
            if not os.path.isabs(trace_file):
                trace_file_path = os.path.join(spec_dir, trace_file)
            else:
                trace_file_path = trace_file

            trace = []
            with open(trace_file_path) as tf:
                for line in tf:
                    trace.append(bool(int(line.strip())))
            self.spot_traces.append(trace)
        
        self.lookahead_hours = 3.0
        self.safety_buffer_factor = 2.0
        self.wait_slack_factor = 4.0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_rem = self.task_duration - sum(self.task_done_time)
        if work_rem <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        current_step = int(time_now / self.env.gap_seconds) if self.env.gap_seconds > 0 else 0
        time_available = self.deadline - time_now

        od_steps_needed = math.ceil(work_rem / self.env.gap_seconds)
        time_for_od_work = od_steps_needed * self.env.gap_seconds
        
        potential_overhead = 0
        if last_cluster_type != ClusterType.ON_DEMAND:
            potential_overhead = self.restart_overhead
        
        time_needed_to_finish_on_od = time_for_od_work + potential_overhead
        safety_buffer = self.restart_overhead * self.safety_buffer_factor

        if time_needed_to_finish_on_od + safety_buffer >= time_available:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        lookahead_steps = int((self.lookahead_hours * 3600) / self.env.gap_seconds)
        lookahead_steps = max(1, lookahead_steps)

        promise = [0.0] * num_regions
        for r_idx in range(num_regions):
            trace = self.spot_traces[r_idx]
            if current_step >= len(trace):
                continue
            
            end_step = min(current_step + lookahead_steps, len(trace))
            future_availability = trace[current_step:end_step]
            
            if future_availability:
                promise[r_idx] = sum(future_availability) / len(future_availability)

        best_region_idx = promise.index(max(promise))
        
        promise_gain = promise[best_region_idx] - promise[current_region]
        cost_of_switch_in_promise = (self.restart_overhead / self.env.gap_seconds) / lookahead_steps
        
        if promise[best_region_idx] > 0 and best_region_idx != current_region and promise_gain > cost_of_switch_in_promise:
            self.env.switch_region(best_region_idx)
            if current_step < len(self.spot_traces[best_region_idx]) and self.spot_traces[best_region_idx][current_step]:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            slack = time_available - time_needed_to_finish_on_od
            wait_threshold = self.restart_overhead * self.wait_slack_factor
            if slack > wait_threshold:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND