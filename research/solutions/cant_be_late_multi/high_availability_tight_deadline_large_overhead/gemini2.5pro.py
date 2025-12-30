import json
from argparse import Namespace
import sys

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-process trace data.
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

        self.trace_files = config.get("trace_files", [])
        self.spot_availability = []
        if not self.trace_files:
            return self

        for trace_file in self.trace_files:
            try:
                with open(trace_file) as tf:
                    trace_data = [
                        line.strip() == '1' for line in tf if line.strip()
                    ]
                    self.spot_availability.append(trace_data)
            except FileNotFoundError:
                pass
        
        if not self.spot_availability or not any(self.spot_availability):
            self.num_timesteps = 0
            self.num_regions = 0
            return self

        self.num_regions = len(self.spot_availability)
        self.num_timesteps = 0
        if self.spot_availability:
            self.num_timesteps = max((len(t) for t in self.spot_availability), default=0)
        
        for r in range(self.num_regions):
            if len(self.spot_availability[r]) < self.num_timesteps:
                padding = [False] * (self.num_timesteps - len(self.spot_availability[r]))
                self.spot_availability[r].extend(padding)

        self.suffix_avail = [[0] * (self.num_timesteps + 1) for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            for t in range(self.num_timesteps - 1, -1, -1):
                self.suffix_avail[r][t] = self.suffix_avail[r][t+1] + self.spot_availability[r][t]
        
        self.panic_buffer_factor = 1.0
        self.wait_buffer_factor = 1.5

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on a heuristic that balances cost and risk.
        """
        if not hasattr(self, 'spot_availability') or not self.spot_availability:
            work_remaining = self.task_duration - sum(self.task_done_time)
            if work_remaining <= 0: return ClusterType.NONE
            if has_spot: return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        work_remaining = self.task_duration - sum(self.task_done_time)
        if work_remaining <= 0:
            return ClusterType.NONE

        elapsed_seconds = self.env.elapsed_seconds
        time_idx = int(elapsed_seconds / self.env.gap_seconds)
        
        if time_idx >= self.num_timesteps:
            return ClusterType.ON_DEMAND

        # 1. Panic Check
        time_if_od = work_remaining + self.restart_overhead
        panic_buffer = self.panic_buffer_factor * self.restart_overhead
        if elapsed_seconds + time_if_od >= self.deadline - panic_buffer:
            return ClusterType.ON_DEMAND

        # 2. Normal Mode: Find and use best SPOT option
        current_region = self.env.get_current_region()

        best_now_spot_region = -1
        max_future_avail = -1
        for r in range(self.num_regions):
            if self.spot_availability[r][time_idx]:
                future_avail = self.suffix_avail[r][time_idx]
                if future_avail > max_future_avail:
                    max_future_avail = future_avail
                    best_now_spot_region = r
        
        if best_now_spot_region != -1:
            if best_now_spot_region != current_region:
                self.env.switch_region(best_now_spot_region)
            return ClusterType.SPOT

        # 3. No SPOT available: Decide between ON_DEMAND and NONE
        time_if_wait = self.env.gap_seconds + work_remaining + self.restart_overhead
        wait_buffer = self.wait_buffer_factor * self.restart_overhead
        
        best_future_spot_region = -1
        max_future_avail_next_step = -1
        next_time_idx = time_idx + 1
        
        if next_time_idx < self.num_timesteps:
             for r in range(self.num_regions):
                future_avail = self.suffix_avail[r][next_time_idx]
                if future_avail > max_future_avail_next_step:
                    max_future_avail_next_step = future_avail
                    best_future_spot_region = r

        if best_future_spot_region != -1 and best_future_spot_region != current_region:
            self.env.switch_region(best_future_spot_region)
        
        if elapsed_seconds + time_if_wait >= self.deadline - wait_buffer:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE