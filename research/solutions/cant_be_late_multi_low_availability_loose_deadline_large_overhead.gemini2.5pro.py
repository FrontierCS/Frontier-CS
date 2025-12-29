import json
from argparse import Namespace
import sys

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses future spot availability traces
    to make decisions, balanced against deadline pressure.
    """

    NAME = "dynamic_lookahead_v2"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-compute
        spot availability lookaheads.
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

        # Load spot availability traces from files
        self.spot_availability_traces = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                trace = [line.strip() == '1' for line in f]
                self.spot_availability_traces.append(trace)

        self.num_regions = len(self.spot_availability_traces)
        if self.env.gap_seconds > 0:
            self.overhead_in_steps = self.restart_overhead / self.env.gap_seconds
            self.total_steps = int(self.deadline / self.env.gap_seconds) + 1
        else:
            self.overhead_in_steps = float('inf')
            self.total_steps = 1
        
        # Pre-compute consecutive spot availability for all future time steps.
        # self.k_values_cache[r][t] stores the number of consecutive spot-available
        # steps in region 'r' starting from time step 't'.
        self.k_values_cache = [[0] * (self.total_steps + 1) for _ in range(self.num_regions)]
        
        for r in range(self.num_regions):
            trace = self.spot_availability_traces[r]
            trace_len = len(trace)
            if trace_len < self.total_steps:
                trace.extend([False] * (self.total_steps - trace_len))

            # Iterate backwards to calculate run lengths efficiently
            for t in range(self.total_steps - 1, -1, -1):
                if trace[t]:
                    self.k_values_cache[r][t] = self.k_values_cache[r][t + 1] + 1
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state and pre-computed lookaheads.
        """
        current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        work_remaining = self.task_duration - sum(self.task_done_time)

        if work_remaining <= 0:
            return ClusterType.NONE

        if current_step >= self.total_steps:
             return ClusterType.ON_DEMAND if work_remaining > 0 else ClusterType.NONE

        time_until_deadline = self.deadline - self.env.elapsed_seconds
        
        current_slack = time_until_deadline - (work_remaining + self.remaining_restart_overhead)

        # PANIC MODE: If slack is less than one restart overhead plus a small buffer,
        # we are in danger. Use the most reliable option to make progress.
        panic_threshold = self.restart_overhead * 1.1
        if current_slack <= panic_threshold:
            return ClusterType.ON_DEMAND

        # NORMAL MODE
        current_region = self.env.get_current_region()
        k_current = self.k_values_cache[current_region][current_step]

        # Find the best alternative region to switch to.
        best_switch_region = -1
        max_k_switch = -1
        for r in range(self.num_regions):
            if r == current_region:
                continue
            k_r = self.k_values_cache[r][current_step]
            if k_r > max_k_switch:
                max_k_switch = k_r
                best_switch_region = r

        # A "risky" move (one that incurs restart_overhead) should only be taken
        # if we have enough slack to absorb the overhead plus a safety buffer.
        risky_move_slack_threshold = self.restart_overhead + panic_threshold

        # Decision 1: Should we switch to another region?
        if current_slack > risky_move_slack_threshold:
            if max_k_switch > k_current + self.overhead_in_steps:
                self.env.switch_region(best_switch_region)
                return ClusterType.SPOT

        # Decision 2: Stay in the current region. Which instance type?
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Switching from reliable ON_DEMAND to risky SPOT incurs an overhead.
                # Only do it if slack is high and the spot window is long enough.
                if (current_slack > risky_move_slack_threshold and 
                        k_current > self.overhead_in_steps):
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT
        else:
            # No spot, and we decided not to switch. Use ON_DEMAND to make progress.
            return ClusterType.ON_DEMAND