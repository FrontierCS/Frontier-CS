import json
import math
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

        self.spot_availability = []
        if "trace_files" in config:
            for trace_file in config["trace_files"]:
                try:
                    with open(trace_file) as tf:
                        self.spot_availability.append([int(line.strip()) for line in tf])
                except (IOError, ValueError):
                    pass

        self.num_timesteps_in_trace = 0
        if self.spot_availability:
            self.num_timesteps_in_trace = len(self.spot_availability[0])

        lookahead_hours = 5.0
        self.lookahead_window_timesteps = 0
        if self.env.gap_seconds > 0:
            self.lookahead_window_timesteps = int(
                lookahead_hours * 3600.0 / self.env.gap_seconds
            )

        return self

    def _find_next_spot_opportunity(self, start_timestep: int, num_regions: int):
        """
        Finds the earliest future timestep with spot availability and the best region at that time.
        """
        if not self.spot_availability or num_regions == 0:
            return float('inf'), -1

        first_t_with_spot = -1
        for t in range(start_timestep + 1, self.num_timesteps_in_trace):
            for r in range(num_regions):
                if self.spot_availability[r][t] == 1:
                    first_t_with_spot = t
                    break
            if first_t_with_spot != -1:
                break
        
        if first_t_with_spot == -1:
            return float('inf'), -1

        soonest_spot_timestep = first_t_with_spot
        best_future_region = -1
        max_future_availability = -1

        for r in range(num_regions):
            if self.spot_availability[r][soonest_spot_timestep] == 1:
                end_window = min(self.num_timesteps_in_trace, soonest_spot_timestep + self.lookahead_window_timesteps)
                future_availability = sum(self.spot_availability[r][soonest_spot_timestep:end_window])
                
                if future_availability > max_future_availability:
                    max_future_availability = future_availability
                    best_future_region = r
        
        return soonest_spot_timestep, best_future_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        total_work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_work_done

        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed_seconds = self.env.elapsed_seconds
        time_to_deadline = self.deadline - elapsed_seconds
        
        if self.env.gap_seconds <= 0:
             return ClusterType.ON_DEMAND
             
        current_timestep = int(elapsed_seconds / self.env.gap_seconds)
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        min_timesteps_needed = math.ceil(remaining_work / self.env.gap_seconds)
        min_time_needed_for_work = min_timesteps_needed * self.env.gap_seconds
        slack = time_to_deadline - min_time_needed_for_work

        if slack <= self.restart_overhead:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self.spot_availability and num_regions > 0:
            best_switch_region = -1
            max_future_availability = -1

            for r in range(num_regions):
                if r == current_region:
                    continue
                
                if current_timestep < self.num_timesteps_in_trace and self.spot_availability[r][current_timestep] == 1:
                    end_window = min(self.num_timesteps_in_trace, current_timestep + self.lookahead_window_timesteps)
                    future_availability = sum(self.spot_availability[r][current_timestep:end_window])
                    
                    if future_availability > max_future_availability:
                        max_future_availability = future_availability
                        best_switch_region = r
            
            if best_switch_region != -1:
                self.env.switch_region(best_switch_region)
                return ClusterType.SPOT

        soonest_spot_timestep, best_future_region = self._find_next_spot_opportunity(current_timestep, num_regions)

        if soonest_spot_timestep == float('inf'):
            return ClusterType.NONE

        wait_timesteps = soonest_spot_timestep - current_timestep
        wait_time_seconds = wait_timesteps * self.env.gap_seconds
        time_cost_of_waiting = wait_time_seconds + self.restart_overhead

        if slack > time_cost_of_waiting:
            if current_region != best_future_region and best_future_region != -1:
                self.env.switch_region(best_future_region)
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
