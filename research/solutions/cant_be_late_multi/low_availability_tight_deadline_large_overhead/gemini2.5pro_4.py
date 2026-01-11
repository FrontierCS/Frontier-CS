import json
from argparse import Namespace
import numpy as np

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that aims to minimize cost by maximizing
    the use of spot instances while ensuring the task completes before the deadline.

    The strategy operates in several stages at each time step:
    1.  **Panic Mode Check:** First, it calculates the absolute latest time it
        must switch to on-demand instances to guarantee finishing by the deadline.
        If the current time is past this point, it immediately chooses on-demand.
    2.  **Region Selection:** If not in panic mode, it evaluates all available
        regions. Each region is scored based on its predicted spot instance
        availability over a future time window. If a different region offers a
        significantly better score that outweighs the time cost of switching,
        the strategy switches to that region.
    3.  **Cluster Type Selection:** In the chosen region, it checks for current
        spot availability.
        - If a spot instance is available, it is always chosen due to its low cost.
        - If spot is not available, the strategy decides between using a costly
          on-demand instance or waiting (incurring no cost). This decision is based
          on a "progress check": it estimates if the total remaining work can be
          completed by a buffered "effective deadline" using only the predicted
          future spot availability in the current region. If it's not on track, it
          uses an on-demand instance to make progress; otherwise, it waits for a
          spot instance to become available.

    This approach balances aggressive cost-saving (preferring spot/waiting) with
    a robust safety net (panic mode and progress checks) to avoid deadline failures.
    Trace data is pre-processed using cumulative sums to allow for highly
    efficient queries of future spot availability.
    """

    NAME = "lookahead_scheduler"

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

        self.traces = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                self.traces.append(np.array(json.load(f), dtype=np.int16))
        
        self.num_regions = len(self.traces)
        
        self.cumulative_traces = [np.cumsum(trace, dtype=np.int32) for trace in self.traces]

        # --- Strategy Parameters ---
        self.lookahead_window_hours = 6.0
        self.buffer_hours = 2.5
        
        # --- Derived Parameters (initialized in first _step call) ---
        self.gap_seconds = None
        self.lookahead_window_steps = None
        self.switch_cost_in_steps = None
        self.max_steps = 0
        self.is_initialized = False

        return self

    def _initialize_params(self):
        """One-time initialization of derived parameters."""
        self.gap_seconds = self.env.gap_seconds
        self.lookahead_window_steps = int(self.lookahead_window_hours * 3600 / self.gap_seconds)
        self.switch_cost_in_steps = self.restart_overhead / self.gap_seconds
        if self.traces:
            self.max_steps = len(self.traces[0])
        self.is_initialized = True

    def _get_future_availability(self, region_idx, start_step, num_steps):
        """
        Calculates the sum of spot availability in a future window using pre-computed sums.
        Window is [start_step, start_step + num_steps).
        """
        if start_step >= self.max_steps or num_steps <= 0:
            return 0
        
        end_step_exclusive = min(start_step + num_steps, self.max_steps)
        
        sum_at_end = self.cumulative_traces[region_idx][end_step_exclusive - 1]
        sum_before_start = self.cumulative_traces[region_idx][start_step - 1] if start_step > 0 else 0
        
        return sum_at_end - sum_before_start

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.is_initialized:
            self._initialize_params()

        # 1. Calculate current state
        elapsed_seconds = self.env.elapsed_seconds
        current_step = int(elapsed_seconds / self.gap_seconds)
        
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = self.deadline - elapsed_seconds

        # 2. Panic Mode: Switch to On-Demand if necessary to guarantee completion
        time_needed_for_ondemand = self.remaining_restart_overhead + remaining_work + self.restart_overhead + self.gap_seconds
        
        if remaining_time <= time_needed_for_ondemand:
            return ClusterType.ON_DEMAND

        # 3. Region Selection Logic
        current_region = self.env.get_current_region()
        
        region_scores = [self._get_future_availability(r, current_step + 1, self.lookahead_window_steps) 
                         for r in range(self.num_regions)]

        best_region_idx = np.argmax(region_scores)
        
        if best_region_idx != current_region:
            current_score = region_scores[current_region]
            best_score = region_scores[best_region_idx]
            if best_score > current_score + self.switch_cost_in_steps:
                self.env.switch_region(best_region_idx)
                current_region = best_region_idx

        # 4. Cluster Type Selection Logic (for the chosen region)
        if current_step < self.max_steps and self.traces[current_region][current_step] == 1:
            return ClusterType.SPOT

        # Spot is not available, decide between ON_DEMAND and NONE.
        effective_deadline = self.deadline - (self.buffer_hours * 3600)
        time_to_effective_deadline = effective_deadline - elapsed_seconds
        
        if time_to_effective_deadline <= 0:
            return ClusterType.ON_DEMAND

        steps_to_effective_deadline = int(time_to_effective_deadline / self.gap_seconds)
        future_spot_steps = self._get_future_availability(current_region, current_step + 1, steps_to_effective_deadline)
        
        remaining_work_steps = remaining_work / self.gap_seconds

        if future_spot_steps < remaining_work_steps:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE