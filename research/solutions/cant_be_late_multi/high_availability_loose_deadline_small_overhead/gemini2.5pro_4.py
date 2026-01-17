import json
from argparse import Namespace
from math import ceil

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    OD_THRESHOLD = 9000.0

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
            with open(trace_file) as tf:
                trace_data = json.load(tf)
                self.spot_availability.append([bool(x) for x in trace_data])

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        time_needed_for_od = work_remaining
        slack = time_remaining - time_needed_for_od

        if slack <= self.OD_THRESHOLD:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        gap_seconds = self.env.gap_seconds
        
        if gap_seconds <= 0:
            return ClusterType.ON_DEMAND
            
        current_timestep = int(current_time // gap_seconds)

        best_spot_region = -1
        for i in range(num_regions):
            region_idx = (current_region + 1 + i) % num_regions
            if region_idx == current_region:
                continue
            
            if current_timestep < len(self.spot_availability[region_idx]) and \
               self.spot_availability[region_idx][current_timestep]:
                best_spot_region = region_idx
                break
        
        if best_spot_region != -1:
            self.env.switch_region(best_spot_region)
            return ClusterType.SPOT

        deadline_timestep = int(self.deadline // gap_seconds)
        next_spot_timestep = -1
        
        max_lookahead = min(deadline_timestep + 1, current_timestep + 100)

        for t_ahead in range(current_timestep + 1, max_lookahead):
            if t_ahead >= len(self.spot_availability[0]):
                break 
            
            for r in range(num_regions):
                if self.spot_availability[r][t_ahead]:
                    next_spot_timestep = t_ahead
                    break
            if next_spot_timestep != -1:
                break
        
        if next_spot_timestep == -1:
            return ClusterType.ON_DEMAND

        wait_steps = next_spot_timestep - current_timestep
        time_lost_by_waiting = wait_steps * gap_seconds

        if (slack - time_lost_by_waiting) > self.OD_THRESHOLD:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND