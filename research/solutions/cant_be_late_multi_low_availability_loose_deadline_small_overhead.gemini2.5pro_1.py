import json
from argparse import Namespace
import os

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

        self.traces = []
        for trace_filename in config["trace_files"]:
            try:
                with open(trace_filename) as f:
                    trace_data = json.load(f)
                    self.traces.append([bool(x) for x in trace_data])
            except (IOError, json.JSONDecodeError):
                self.traces.append([])

        self.num_regions = len(self.traces)

        if self.traces and self.traces[0] and self.deadline > 0:
            num_trace_steps = len(self.traces[0])
            if num_trace_steps > 0:
                self.gap_seconds = self.deadline / num_trace_steps
            else:
                self.gap_seconds = 3600.0  # Fallback
        else:
            self.gap_seconds = 3600.0  # Fallback

        self.panic_safety_buffer_seconds = 3600.0
        self.wait_threshold_multiplier = 1.5

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        elapsed_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - elapsed_time

        if time_to_deadline <= 0:
            return ClusterType.NONE

        required_time_on_demand = work_remaining
        if last_cluster_type != ClusterType.ON_DEMAND:
            required_time_on_demand += self.restart_overhead

        if time_to_deadline <= required_time_on_demand + self.panic_safety_buffer_seconds:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        
        time_idx = int(elapsed_time // self.gap_seconds)
        
        if has_spot:
            return ClusterType.SPOT

        best_alt_region = -1
        for i in range(1, self.num_regions):
            region_to_check = (current_region + i) % self.num_regions
            
            trace = self.traces[region_to_check]
            if time_idx < len(trace) and trace[time_idx]:
                best_alt_region = region_to_check
                break
        
        if best_alt_region != -1:
            self.env.switch_region(best_alt_region)
            return ClusterType.SPOT

        if time_to_deadline > work_remaining * self.wait_threshold_multiplier:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
