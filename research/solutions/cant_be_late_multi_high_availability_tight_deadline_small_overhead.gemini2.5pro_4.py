import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-process traces.
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

        # Pre-process traces for efficient lookahead in _step
        self.num_steps = int(self.deadline / self.env.gap_seconds) + 2
        
        self.spot_availability = []
        trace_files = config["trace_files"]
        num_regions = self.env.get_num_regions()

        for i in range(num_regions):
            trace_file = trace_files[i]
            with open(trace_file) as f:
                trace = [int(line.strip()) for line in f if line.strip()]
                if len(trace) < self.num_steps:
                    trace.extend([0] * (self.num_steps - len(trace)))
                self.spot_availability.append(trace[:self.num_steps])

        # Pre-compute lookahead information for O(1) access in _step
        self.precomputed_runs = [[0] * self.num_steps for _ in range(num_regions)]
        self.precomputed_next_spot = [[self.num_steps] * self.num_steps for _ in range(num_regions)]

        for r in range(num_regions):
            # Precompute future consecutive spot runs
            current_run = 0
            for i in range(self.num_steps - 1, -1, -1):
                if self.spot_availability[r][i] == 1:
                    current_run += 1
                else:
                    current_run = 0
                self.precomputed_runs[r][i] = current_run
            
            # Precompute next spot availability step
            last_seen_spot = self.num_steps
            for i in range(self.num_steps - 1, -1, -1):
                if self.spot_availability[r][i] == 1:
                    last_seen_spot = i
                self.precomputed_next_spot[r][i] = last_seen_spot
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state and pre-computed trace data.
        """
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        
        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        # Define a safety buffer for the panic mode threshold.
        safety_buffer = self.restart_overhead + 3600.0
        
        # Panic mode: If remaining slack is less than the buffer, use on-demand.
        if time_to_deadline <= remaining_work + safety_buffer:
            return ClusterType.ON_DEMAND
            
        current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        
        if current_step >= self.num_steps:
            return ClusterType.ON_DEMAND

        # Normal mode: Prefer spot instances.
        if has_spot:
            return ClusterType.SPOT

        # Current region does not have spot. Evaluate other options.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Option 1: Switch to another region that has spot available now.
        best_switch_region = -1
        max_run_len = 0
        
        for r in range(num_regions):
            if r == current_region:
                continue
            
            if self.spot_availability[r][current_step] == 1:
                run_len = self.precomputed_runs[r][current_step]
                if run_len > max_run_len:
                    max_run_len = run_len
                    best_switch_region = r
        
        if best_switch_region != -1:
            self.env.switch_region(best_switch_region)
            return ClusterType.SPOT
            
        # Option 2: No other region has spot now. Decide whether to wait or use on-demand.
        next_step_to_check = current_step + 1
        if next_step_to_check >= self.num_steps:
            return ClusterType.ON_DEMAND

        earliest_next_spot_step = self.num_steps
        for r in range(num_regions):
            next_spot_in_r = self.precomputed_next_spot[r][next_step_to_check]
            if next_spot_in_r < earliest_next_spot_step:
                earliest_next_spot_step = next_spot_in_r

        if earliest_next_spot_step >= self.num_steps:
            return ClusterType.ON_DEMAND
            
        wait_time = (earliest_next_spot_step - current_step) * self.env.gap_seconds
        
        current_slack = time_to_deadline - remaining_work
        if current_slack > wait_time + safety_buffer:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
