import json
from argparse import Namespace
import math
import sys

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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

        # --- Hyperparameters ---
        self.FUTURE_WINDOW_HOURS = 4.0
        self.PANIC_SAFETY_MARGIN_FACTOR = 2.0
        self.SWITCH_SLACK_BUFFER_FACTOR = 2.0
        self.SCORE_GAIN_THRESHOLD = 1.05
        self.OD_SLACK_THRESHOLD_HOURS = 2.0

        # --- Pre-computation of spot availability ---
        self.spot_availability = []
        try:
            for trace_file in config["trace_files"]:
                with open(trace_file) as tf:
                    trace = [line.strip() == '1' for line in tf]
                    self.spot_availability.append(trace)
        except (IOError, IndexError):
            self.spot_availability = []

        if not self.spot_availability or not self.spot_availability[0]:
            self.time_steps = 0
            self.num_regions_from_traces = 0
            self.future_spot_counts = []
            return self

        self.time_steps = len(self.spot_availability[0])
        self.num_regions_from_traces = len(self.spot_availability)

        # Pre-calculate future spot counts using a sliding window for efficiency
        self.future_spot_counts = []
        if self.gap_seconds > 0:
            window_steps = math.ceil(self.FUTURE_WINDOW_HOURS * 3600 / self.gap_seconds)
        else:
            window_steps = 0

        for r_idx in range(self.num_regions_from_traces):
            trace_int = [int(v) for v in self.spot_availability[r_idx]]
            counts = [0] * self.time_steps
            if self.time_steps > 0:
                # Initial window sum for t=0
                current_sum = sum(trace_int[0:min(window_steps, self.time_steps)])
                counts[0] = current_sum

                for t_idx in range(1, self.time_steps):
                    # Efficiently update sum by sliding the window
                    new_count = counts[t_idx - 1] - trace_int[t_idx - 1]
                    if t_idx + window_steps - 1 < self.time_steps:
                        new_count += trace_int[t_idx + window_steps - 1]
                    counts[t_idx] = new_count
            
            self.future_spot_counts.append(counts)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-9:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        current_region = self.env.get_current_region()
        
        current_time_idx = math.floor(current_time / self.gap_seconds) if self.gap_seconds > 0 else 0
        
        if current_time_idx >= self.time_steps:
            current_time_idx = self.time_steps - 1
        
        # 1. Panic Mode: Must use ON_DEMAND if deadline is approaching
        time_available = self.deadline - current_time
        panic_safety_margin = self.PANIC_SAFETY_MARGIN_FACTOR * self.restart_overhead
        time_needed_for_od = work_remaining + panic_safety_margin

        if time_available <= time_needed_for_od:
            return ClusterType.ON_DEMAND

        # 2. Best Case: Spot is available in the current region
        if has_spot:
            return ClusterType.SPOT

        # 3. No Spot Locally: Evaluate switching to another region
        num_regions_in_env = self.env.get_num_regions()
        if self.spot_availability and num_regions_in_env == self.num_regions_from_traces:
            candidate_regions = []
            for r in range(num_regions_in_env):
                if r != current_region and self.spot_availability[r][current_time_idx]:
                    candidate_regions.append(r)

            if candidate_regions:
                slack = time_available - work_remaining
                switch_slack_buffer = self.SWITCH_SLACK_BUFFER_FACTOR * self.restart_overhead
                
                if slack > self.restart_overhead + switch_slack_buffer:
                    best_new_region = max(
                        candidate_regions, 
                        key=lambda r: self.future_spot_counts[r][current_time_idx]
                    )
                    
                    current_score = self.future_spot_counts[current_region][current_time_idx]
                    best_new_score = self.future_spot_counts[best_new_region][current_time_idx]

                    if best_new_score > current_score * self.SCORE_GAIN_THRESHOLD:
                        self.env.switch_region(best_new_region)
                        return ClusterType.SPOT

        # 4. No Spot Anywhere (or not worth switching): Decide between ON_DEMAND and NONE
        if self.spot_availability and 0 <= current_region < self.num_regions_from_traces:
            future_spot_here = self.future_spot_counts[current_region][current_time_idx]
            if future_spot_here == 0:
                return ClusterType.ON_DEMAND

        slack = time_available - work_remaining
        od_slack_threshold = self.OD_SLACK_THRESHOLD_HOURS * 3600

        if slack < od_slack_threshold:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE