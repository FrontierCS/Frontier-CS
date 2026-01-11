import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "lookahead_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        Loads traces and pre-computes data for efficient step decisions.
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

        # Load all trace data into memory
        self.traces = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                trace_data = [bool(int(line.strip())) for line in f.readlines()]
                self.traces.append(trace_data)

        self.num_regions = len(self.traces)
        self.trace_len = len(self.traces[0]) if self.traces else 0

        # Hyperparameters
        lookahead_hours = 4.0
        if self.env.gap_seconds > 0:
            self.lookahead_window = max(1, int(lookahead_hours * 3600 / self.env.gap_seconds))
        else:
            self.lookahead_window = 1

        self.switch_threshold = 1.0

        caution_buffer_factor = 0.10
        self.caution_buffer = caution_buffer_factor * self.task_duration

        # Pre-computation for performance using cumulative sum arrays
        self.future_spot_sums = []
        if self.traces:
            for r in range(self.num_regions):
                trace = self.traces[r]
                cumulative_sum = [0] * (self.trace_len + 1)
                for i in range(self.trace_len):
                    cumulative_sum[i + 1] = cumulative_sum[i] + trace[i]
                self.future_spot_sums.append(cumulative_sum)

        return self

    def get_future_spot_count(self, region_idx: int, start_step: int, window_size: int) -> int:
        """
        Calculates future spot availability for a region using the pre-computed data.
        """
        if not self.future_spot_sums or region_idx >= len(self.future_spot_sums):
            return 0

        cumulative_sum = self.future_spot_sums[region_idx]
        
        start = start_step
        end = min(start_step + window_size, self.trace_len)

        if start >= end:
            return 0
        
        return cumulative_sum[end] - cumulative_sum[start]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed
        
        # 1. Panic Mode: Must use ON_DEMAND to guarantee completion.
        time_needed_for_od = work_remaining + self.restart_overhead
        if time_needed_for_od >= time_left:
            return ClusterType.ON_DEMAND

        # 2. Primary Strategy: Use SPOT if available in the current region.
        if has_spot:
            return ClusterType.SPOT

        # 3. No Spot in Current Region: Evaluate other options.
        current_time_step = int(time_elapsed / self.env.gap_seconds) if self.env.gap_seconds > 0 else 0
        
        if current_time_step >= self.trace_len:
            # Past trace data; fall back to cautious ON_DEMAND vs. NONE decision.
            time_needed_cautious = work_remaining + self.restart_overhead
            if time_elapsed + time_needed_cautious + self.caution_buffer >= self.deadline:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

        # 3a. Look for a better region to switch to.
        best_j = -1
        best_future_spot_count = -1
        current_region = self.env.get_current_region()

        # Find the best alternative region that has spot available NOW.
        for j in range(self.num_regions):
            if j != current_region and self.traces[j][current_time_step]:
                future_count = self.get_future_spot_count(j, current_time_step, self.lookahead_window)
                if future_count > best_future_spot_count:
                    best_future_spot_count = future_count
                    best_j = j
        
        # Evaluate if the switch is beneficial and safe.
        if best_j != -1:
            current_region_future_count = self.get_future_spot_count(
                current_region, current_time_step, self.lookahead_window
            )
            
            # Check if the new region is significantly better.
            if best_future_spot_count > current_region_future_count + self.switch_threshold:
                # Check if we can afford the time cost of a switch, including a
                # worst-case subsequent preemption.
                work_after_switch = work_remaining + self.restart_overhead
                time_needed_after_switch_worst_case = work_after_switch + self.restart_overhead
                
                if time_needed_after_switch_worst_case < time_left:
                    self.env.switch_region(best_j)
                    return ClusterType.SPOT

        # 3b. No good switch: Decide between ON_DEMAND and NONE.
        time_needed_cautious = work_remaining + self.restart_overhead
        if time_elapsed + time_needed_cautious + self.caution_buffer >= self.deadline:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE