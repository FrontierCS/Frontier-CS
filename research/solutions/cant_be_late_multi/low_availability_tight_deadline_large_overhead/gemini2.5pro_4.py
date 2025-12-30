import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
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

        self.SWITCH_ISLAND_HEADROOM = 1.5
        self.WAIT_SLACK_HEADROOM = 2.0
        self.WAIT_MAX_DURATION = 1.0
        self.CRITICAL_SLACK_BUFFER_FACTOR = 1.1

        self.spot_availability = []
        if "trace_files" in config and config["trace_files"]:
            for trace_file in config["trace_files"]:
                with open(trace_file) as f:
                    trace_data = json.load(f)["spot"]
                    self.spot_availability.append(trace_data)

        self.num_regions_from_traces = len(self.spot_availability)
        self.precomputed = self.num_regions_from_traces == 0

        self.critical_slack_buffer = self.restart_overhead * self.CRITICAL_SLACK_BUFFER_FACTOR
        
        return self

    def _precompute_if_needed(self):
        if self.precomputed:
            return

        self.num_timesteps = len(self.spot_availability[0])
        self._precompute_trace_insights()
        self.precomputed = True

    def _precompute_trace_insights(self):
        gap_seconds = self.env.gap_seconds
        self.spot_island_length = [[0] * self.num_timesteps for _ in range(self.num_regions_from_traces)]
        self.time_to_next_spot = [[0] * self.num_timesteps for _ in range(self.num_regions_from_traces)]

        for r in range(self.num_regions_from_traces):
            # Backwards pass for spot_island_length
            if self.spot_availability[r][-1] == 1:
                self.spot_island_length[r][-1] = gap_seconds
            for t in range(self.num_timesteps - 2, -1, -1):
                if self.spot_availability[r][t] == 1:
                    self.spot_island_length[r][t] = gap_seconds + self.spot_island_length[r][t + 1]
                else:
                    self.spot_island_length[r][t] = 0.0

            # Backwards pass for time_to_next_spot
            if self.spot_availability[r][-1] == 0:
                self.time_to_next_spot[r][-1] = float('inf')
            else:
                self.time_to_next_spot[r][-1] = 0.0
                
            for t in range(self.num_timesteps - 2, -1, -1):
                if self.spot_availability[r][t] == 0:
                    self.time_to_next_spot[r][t] = gap_seconds + self.time_to_next_spot[r][t + 1]
                else:
                    self.time_to_next_spot[r][t] = 0.0


    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._precompute_if_needed()

        if self.num_regions_from_traces == 0:
            return self._simple_step(last_cluster_type, has_spot)

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        elapsed_seconds = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed_seconds
        
        if time_remaining < work_remaining:
            return ClusterType.ON_DEMAND
        
        current_timestep = int(elapsed_seconds / self.env.gap_seconds)
        if current_timestep >= self.num_timesteps:
            return self._simple_step(last_cluster_type, has_spot)
            
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        slack = time_remaining - work_remaining
        overhead_if_switch_to_od = self.restart_overhead if last_cluster_type != ClusterType.ON_DEMAND else 0.0

        if slack < overhead_if_switch_to_od + self.critical_slack_buffer:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        best_region_to_switch = -1
        max_island_duration = 0

        for r in range(num_regions):
            if r == current_region:
                continue
            
            if r < self.num_regions_from_traces and self.spot_availability[r][current_timestep] == 1:
                duration = self.spot_island_length[r][current_timestep]
                if duration > max_island_duration:
                    max_island_duration = duration
                    best_region_to_switch = r
        
        if best_region_to_switch != -1 and max_island_duration > self.SWITCH_ISLAND_HEADROOM * self.restart_overhead:
            self.env.switch_region(best_region_to_switch)
            return ClusterType.SPOT

        if current_region < self.num_regions_from_traces:
            next_spot_wait_time = self.time_to_next_spot[current_region][current_timestep]
            
            if slack > self.WAIT_SLACK_HEADROOM * self.restart_overhead and \
               next_spot_wait_time <= self.WAIT_MAX_DURATION * self.restart_overhead:
               return ClusterType.NONE

        return ClusterType.ON_DEMAND
        
    def _simple_step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_remaining = self.deadline - self.env.elapsed_seconds
        
        if time_remaining < work_remaining + self.restart_overhead:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND