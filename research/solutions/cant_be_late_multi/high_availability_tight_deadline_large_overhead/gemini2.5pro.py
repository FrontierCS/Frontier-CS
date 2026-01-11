import json
import os
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "predictive_slack_based"

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
        spec_dir = os.path.dirname(os.path.abspath(spec_path))
        for trace_file in config["trace_files"]:
            full_trace_path = os.path.join(spec_dir, trace_file)
            region_trace = []
            try:
                with open(full_trace_path) as tf:
                    for line in tf:
                        line = line.strip()
                        if line:
                            availability = int(line.split(',')[0])
                            region_trace.append(availability == 1)
            except (FileNotFoundError, ValueError, IndexError):
                # In case of file issues, assume no availability
                pass
            self.spot_availability.append(region_trace)
        
        self.num_regions = len(self.spot_availability)
        
        if self.env and hasattr(self.env, 'gap_seconds') and self.deadline is not None:
            self.total_timesteps = int(self.deadline / self.env.gap_seconds) + 5
            for i in range(self.num_regions):
                if len(self.spot_availability[i]) < self.total_timesteps:
                    padding = [False] * (self.total_timesteps - len(self.spot_availability[i]))
                    self.spot_availability[i].extend(padding)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done
        
        if work_rem <= 0:
            return ClusterType.NONE

        t_current = self.env.elapsed_seconds
        t_idx = int(t_current / self.env.gap_seconds)
        time_rem = self.deadline - t_current
        current_region = self.env.get_current_region()
        slack = time_rem - work_rem

        if slack < self.restart_overhead:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        best_uptime = 0
        best_switch_region = -1
        for r in range(self.num_regions):
            if r == current_region:
                continue
            
            if t_idx < len(self.spot_availability[r]) and self.spot_availability[r][t_idx]:
                uptime = 0
                for k in range(t_idx, len(self.spot_availability[r])):
                    if self.spot_availability[r][k]:
                        uptime += 1
                    else:
                        break
                if uptime > best_uptime:
                    best_uptime = uptime
                    best_switch_region = r

        wait_steps = 0
        limit = len(self.spot_availability[current_region]) if current_region < self.num_regions else 0
        for k in range(t_idx, limit):
            if self.spot_availability[current_region][k]:
                break
            wait_steps += 1
        else:
            wait_steps = float('inf')

        time_cost_switch = self.restart_overhead
        time_cost_wait = wait_steps * self.env.gap_seconds
        
        if best_switch_region != -1 and time_cost_switch < time_cost_wait:
            if slack >= time_cost_switch:
                self.env.switch_region(best_switch_region)
                return ClusterType.SPOT

        if slack >= time_cost_wait:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND