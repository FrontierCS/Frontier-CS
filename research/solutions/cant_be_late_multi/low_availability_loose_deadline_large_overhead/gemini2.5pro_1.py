import json
import math
import numpy as np
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses pre-computation on spot traces
    to make informed decisions.
    """

    NAME = "precompute_heuristic"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-compute lookup tables.
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

        self.gap = self.env.gap_seconds
        if self.gap == 0:
            self.overhead_steps = 0
        else:
            self.overhead_steps = math.ceil(self.restart_overhead / self.gap)

        self.traces = []
        max_trace_len = 0
        if "trace_files" in config:
            for trace_file in config["trace_files"]:
                try:
                    with open(trace_file) as f:
                        trace_data = json.load(f)
                        self.traces.append(trace_data)
                        if len(trace_data) > max_trace_len:
                            max_trace_len = len(trace_data)
                except (FileNotFoundError, json.JSONDecodeError):
                    self.traces.append([])

        self.num_regions = len(self.traces)
        if self.num_regions == 0:
            return self

        deadline_steps = 0
        if self.gap > 0:
            deadline_steps = int(math.ceil(self.deadline / self.gap))
        
        self.max_steps = max(max_trace_len, deadline_steps) + 10

        padded_traces_list = []
        for trace in self.traces:
            current_len = len(trace)
            if current_len >= self.max_steps:
                padded_traces_list.append(trace[:self.max_steps])
            else:
                padding_needed = self.max_steps - current_len
                padded_traces_list.append(trace + [0] * padding_needed)

        traces_np = np.array(padded_traces_list, dtype=np.int8)

        self.spot_block_lengths = np.zeros_like(traces_np, dtype=np.int32)
        for r in range(self.num_regions):
            for t in range(self.max_steps - 2, -1, -1):
                if traces_np[r, t] == 1:
                    self.spot_block_lengths[r, t] = 1 + self.spot_block_lengths[r, t + 1]

        infinity = self.max_steps
        next_spot_per_region = np.full((self.num_regions, self.max_steps), infinity, dtype=np.int32)
        for r in range(self.num_regions):
            next_s = infinity
            for t in range(self.max_steps - 1, -1, -1):
                if traces_np[r, t] == 1:
                    next_s = t
                next_spot_per_region[r, t] = next_s

        min_next_spot_step = np.min(next_spot_per_region, axis=0)
        min_next_spot_region = np.argmin(next_spot_per_region, axis=0)
        self.next_spot_start_info = np.stack([min_next_spot_step, min_next_spot_region], axis=1)
        
        self.PANIC_BUFFER = 1.1
        self.SWITCH_THRESHOLD_STEPS = self.overhead_steps

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on pre-computed data and current state.
        """
        work_rem_secs = self.task_duration - sum(self.task_done_time)
        if work_rem_secs <= 0:
            return ClusterType.NONE

        if self.num_regions == 0:
            return ClusterType.ON_DEMAND

        t_idx = 0
        if self.gap > 0:
            t_idx = int(round(self.env.elapsed_seconds / self.gap))
            
        if t_idx >= self.max_steps:
            return ClusterType.ON_DEMAND

        time_rem_secs = self.deadline - self.env.elapsed_seconds
        
        if time_rem_secs <= work_rem_secs + self.restart_overhead * self.PANIC_BUFFER:
            return ClusterType.ON_DEMAND

        L = self.spot_block_lengths[:, t_idx]
        r_best = int(np.argmax(L))
        L_max = L[r_best]

        if L_max == 0:
            next_start_step, _ = self.next_spot_start_info[t_idx]
            
            if next_start_step >= self.max_steps:
                return ClusterType.ON_DEMAND

            wait_time_secs = (next_start_step - t_idx) * self.gap
            
            if time_rem_secs - wait_time_secs > work_rem_secs + self.restart_overhead * self.PANIC_BUFFER:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
        else:
            current_region = self.env.get_current_region()
            L_current = L[current_region]

            if r_best != current_region and L_max > L_current + self.SWITCH_THRESHOLD_STEPS:
                self.env.switch_region(r_best)
                return ClusterType.SPOT
            else:
                if has_spot:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND