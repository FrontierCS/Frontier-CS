import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    Your multi-region scheduling strategy.
    """
    NAME = "foresight_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-process traces.
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

        self.num_regions = self.env.get_num_regions()
        
        self.spot_availability = []
        min_len = float('inf')
        if "trace_files" in config and config["trace_files"]:
            for trace_file in config["trace_files"]:
                with open(trace_file) as f:
                    trace = [line.strip() == '1' for line in f]
                    self.spot_availability.append(trace)
                    if len(trace) > 0:
                        min_len = min(min_len, len(trace))
        
        if min_len == float('inf'):
             min_len = 0

        self.num_steps = min_len
        # Ensure spot_availability list is truncated to the shortest trace length
        temp_spot_availability = []
        for i in range(len(self.spot_availability)):
            temp_spot_availability.append(self.spot_availability[i][:self.num_steps])
        self.spot_availability = temp_spot_availability
        
        # The number of regions is determined by the number of traces provided
        self.num_regions = len(self.spot_availability)

        # Pre-calculate spot run lengths (consecutive availability)
        self.spot_run_length = [[0] * self.num_steps for _ in range(self.num_regions)]
        if self.num_steps > 0:
            for r in range(self.num_regions):
                if self.spot_availability[r][self.num_steps - 1]:
                    self.spot_run_length[r][self.num_steps - 1] = 1
                for t in range(self.num_steps - 2, -1, -1):
                    if self.spot_availability[r][t]:
                        self.spot_run_length[r][t] = 1 + self.spot_run_length[r][t + 1]

        # Pre-calculate next best spot opportunity for each time step
        self.next_spot_info = [(self.num_steps, -1)] * (self.num_steps + 1)
        if self.num_steps > 0:
            for t in range(self.num_steps - 1, -1, -1):
                best_region_at_t = -1
                max_run_len_at_t = -1
                for r in range(self.num_regions):
                    if self.spot_availability[r][t] and self.spot_run_length[r][t] > max_run_len_at_t:
                        max_run_len_at_t = self.spot_run_length[r][t]
                        best_region_at_t = r
                
                if best_region_at_t != -1:
                    self.next_spot_info[t] = (t, best_region_at_t)
                else:
                    self.next_spot_info[t] = self.next_spot_info[t+1]

        self.time_buffer = 1e-6

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on pre-computed trace data and current state.
        """
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        if remaining_work <= self.time_buffer:
            return ClusterType.NONE

        time_to_deadline = self.deadline - current_time
        slack = time_to_deadline - remaining_work
        
        current_step_idx = math.floor(current_time / self.env.gap_seconds)
        if current_step_idx >= self.num_steps:
            return ClusterType.ON_DEMAND
            
        if slack <= self.restart_overhead + self.time_buffer:
            return ClusterType.ON_DEMAND

        best_r_now = -1
        max_run_now = -1
        for r in range(self.num_regions):
            if self.spot_availability[r][current_step_idx]:
                if self.spot_run_length[r][current_step_idx] > max_run_now:
                    max_run_now = self.spot_run_length[r][current_step_idx]
                    best_r_now = r

        if best_r_now != -1:
            current_region = self.env.get_current_region()
            needs_restart = (best_r_now != current_region) or (last_cluster_type != ClusterType.SPOT)
            
            if not needs_restart or slack > self.restart_overhead + self.time_buffer:
                if best_r_now != current_region:
                    self.env.switch_region(best_r_now)
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        next_spot_step, next_spot_region = self.next_spot_info[current_step_idx]

        if next_spot_region == -1:
            return ClusterType.ON_DEMAND

        wait_steps = next_spot_step - current_step_idx
        wait_time = wait_steps * self.env.gap_seconds
        
        if slack > wait_time + self.restart_overhead + self.time_buffer:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND