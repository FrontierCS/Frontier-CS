import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "expert_planner"  # REQUIRED: unique identifier

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
        if "trace_files" in config:
            for trace_file in config["trace_files"]:
                try:
                    with open(trace_file) as f:
                        trace = [line.strip() == '1' for line in f if line.strip()]
                        self.spot_availability.append(trace)
                except FileNotFoundError:
                    self.spot_availability.append([])

        self.num_regions = len(self.spot_availability)
        self.max_trace_len = 0
        if self.spot_availability:
            non_empty_traces = [t for t in self.spot_availability if t]
            if non_empty_traces:
                self.max_trace_len = max(len(t) for t in non_empty_traces)

        self.consecutive_spot_counts = []
        for r in range(self.num_regions):
            trace = self.spot_availability[r]
            padded_trace = trace + [False] * (self.max_trace_len - len(trace))
            counts = [0] * self.max_trace_len
            if not self.max_trace_len:
                self.consecutive_spot_counts.append([])
                continue
            
            count = 0
            for i in range(self.max_trace_len - 1, -1, -1):
                if padded_trace[i]:
                    count += 1
                else:
                    count = 0
                counts[i] = count
            self.consecutive_spot_counts.append(counts)
            
        self.PANIC_SLACK_FACTOR = 1.5
        self.SWITCH_GAIN_THRESHOLD = 1.0

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
        work_rem = self.task_duration - work_done
        if work_rem <= 0:
            return ClusterType.NONE

        gap_seconds = self.env.gap_seconds
        if gap_seconds <= 0: # Avoid division by zero
            return ClusterType.ON_DEMAND

        t_current_step = int(self.env.elapsed_seconds / gap_seconds)
        deadline_step = int(self.deadline / gap_seconds)

        if t_current_step >= deadline_step:
            return ClusterType.NONE

        steps_rem = deadline_step - t_current_step
        overhead_steps = math.ceil(self.restart_overhead / gap_seconds)
        work_rem_steps = math.ceil(work_rem / gap_seconds)

        od_needed_steps = work_rem_steps + overhead_steps
        slack_steps = steps_rem - od_needed_steps

        panic_threshold_steps = math.ceil(overhead_steps * self.PANIC_SLACK_FACTOR)
        if slack_steps <= panic_threshold_steps:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        if t_current_step >= self.max_trace_len or not self.consecutive_spot_counts:
            return ClusterType.SPOT if has_spot else ClusterType.NONE

        best_region_idx = -1
        max_consecutive_spots = -1
        for r in range(self.num_regions):
            spots = self.consecutive_spot_counts[r][t_current_step]
            if spots > max_consecutive_spots:
                max_consecutive_spots = spots
                best_region_idx = r
        
        if best_region_idx != -1 and current_region != best_region_idx:
            current_region_spots = self.consecutive_spot_counts[current_region][t_current_step]
            
            if max_consecutive_spots > current_region_spots + overhead_steps + self.SWITCH_GAIN_THRESHOLD:
                self.env.switch_region(best_region_idx)
                return ClusterType.SPOT

        return ClusterType.SPOT if has_spot else ClusterType.NONE
