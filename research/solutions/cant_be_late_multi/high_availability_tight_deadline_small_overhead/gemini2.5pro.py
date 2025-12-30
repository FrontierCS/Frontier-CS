import json
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

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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
        spec_dir = os.path.dirname(os.path.abspath(spec_path))
        
        for trace_file in config["trace_files"]:
            full_trace_path = os.path.join(spec_dir, trace_file)
            availability_data = []
            try:
                with open(full_trace_path, 'r') as f:
                    for line in f:
                        val = line.strip().lower()
                        availability_data.append(val in ('true', '1'))
            except FileNotFoundError:
                # Handle cases where trace file might not exist in some environments
                pass
            self.spot_availability.append(availability_data)

        self.num_regions = len(self.spot_availability)
        self.max_timesteps = 0
        if self.num_regions > 0 and self.spot_availability[0]:
            self.max_timesteps = len(self.spot_availability[0])
        
        # Hyperparameters for the strategy
        self.lookahead_window = 5
        self.wait_steps_threshold = 5

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_to_deadline = self.deadline - time_now
        
        time_needed_on_demand = work_remaining + self.remaining_restart_overhead
        
        if time_now + time_needed_on_demand >= self.deadline:
            return ClusterType.ON_DEMAND

        slack = time_to_deadline - time_needed_on_demand

        safety_margin = self.env.gap_seconds + self.restart_overhead
        if slack <= safety_margin:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        if has_spot:
            return ClusterType.SPOT
        
        t_idx = int(round(time_now / self.env.gap_seconds))

        if t_idx >= self.max_timesteps or not self.spot_availability:
            return ClusterType.ON_DEMAND

        best_alt_region = -1
        best_future_availability = -1
        
        for r in range(self.num_regions):
            if r == current_region:
                continue
            
            try:
                if self.spot_availability[r][t_idx]:
                    future_end = min(t_idx + 1 + self.lookahead_window, self.max_timesteps)
                    future_avail = sum(self.spot_availability[r][t_idx+1:future_end])

                    if future_avail > best_future_availability:
                        best_future_availability = future_avail
                        best_alt_region = r
            except IndexError:
                continue
        
        if best_alt_region != -1:
            self.env.switch_region(best_alt_region)
            return ClusterType.SPOT

        comfortable_slack_margin = safety_margin + self.wait_steps_threshold * self.env.gap_seconds
        if slack > comfortable_slack_margin:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND