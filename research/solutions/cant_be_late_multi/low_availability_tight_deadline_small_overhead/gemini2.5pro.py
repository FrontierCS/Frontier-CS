import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "Cant-Be-Late_v1.1"

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
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                self.spot_availability.append(
                    tuple(line.strip() == '1' for line in f)
                )

        self.patience_steps = 1
        self.lookahead_window = 12

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        if self.env.gap_seconds > 0:
            steps_needed = math.ceil(work_remaining / self.env.gap_seconds)
        else:
            steps_needed = float('inf') if work_remaining > 0 else 0
        
        time_needed_for_od = (steps_needed * self.env.gap_seconds) + self.restart_overhead
        
        if self.env.elapsed_seconds + time_needed_for_od >= self.deadline:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        current_time_idx = int(self.env.elapsed_seconds / self.env.gap_seconds)
        num_regions = self.env.get_num_regions()
        current_region_idx = self.env.get_current_region()

        best_region_to_switch = -1
        max_future_spot = 0
        
        for r_idx in range(num_regions):
            if r_idx == current_region_idx:
                continue

            trace = self.spot_availability[r_idx]
            if current_time_idx < len(trace) and trace[current_time_idx]:
                future_spot_steps = 0
                for t_offset in range(self.lookahead_window):
                    check_idx = current_time_idx + t_offset
                    if check_idx < len(trace) and trace[check_idx]:
                        future_spot_steps += 1
                    else:
                        break
                
                if future_spot_steps > max_future_spot:
                    max_future_spot = future_spot_steps
                    best_region_to_switch = r_idx

        if best_region_to_switch != -1:
            self.env.switch_region(best_region_to_switch)
            return ClusterType.SPOT

        min_wait_steps = float('inf')
        for r_idx in range(num_regions):
            trace = self.spot_availability[r_idx]
            for t_offset in range(1, self.lookahead_window + 1):
                check_idx = current_time_idx + t_offset
                if check_idx < len(trace) and trace[check_idx]:
                    min_wait_steps = min(min_wait_steps, t_offset)
                    break
        
        if min_wait_steps <= self.patience_steps:
            slack_seconds = self.deadline - (self.env.elapsed_seconds + time_needed_for_od)
            wait_time_seconds = min_wait_steps * self.env.gap_seconds
            
            if wait_time_seconds < slack_seconds:
                return ClusterType.NONE

        return ClusterType.ON_DEMAND