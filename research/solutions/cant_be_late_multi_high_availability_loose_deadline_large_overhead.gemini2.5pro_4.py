import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "planner_strategy"  # REQUIRED: unique identifier

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

        # Post-initialization setup
        self.gap_seconds = self.env.gap_seconds
        self.num_regions = self.env.get_num_regions()

        # Load spot availability traces
        self.spot_traces = []
        for trace_path in config['trace_files']:
            with open(trace_path) as f:
                trace = [int(line.strip()) for line in f]
                self.spot_traces.append(trace)

        # Pre-calculate cost parameters
        self.on_demand_price_per_hr = 3.06
        self.spot_price_per_hr = 0.9701
        self.od_cost_per_step = self.on_demand_price_per_hr * (self.gap_seconds / 3600.0)
        self.spot_cost_per_step = self.spot_price_per_hr * (self.gap_seconds / 3600.0)
        
        # Pre-calculate overhead in steps
        if self.gap_seconds > 0:
            self.overhead_in_steps = math.ceil(self.restart_overhead / self.gap_seconds)
        else:
            self.overhead_in_steps = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. State Calculation
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - current_time
        effective_work_left = work_left + self.remaining_restart_overhead
        current_timestep = int(current_time / self.gap_seconds)
        current_region = self.env.get_current_region()

        # 2. Panic Mode Check: If not enough time left even with pure on-demand,
        # use on-demand to guarantee progress.
        if time_left <= effective_work_left:
            return ClusterType.ON_DEMAND

        # 3. Region Selection: Estimate cost to finish in each region and pick the cheapest.
        work_steps_left = math.ceil(work_left / self.gap_seconds) if self.gap_seconds > 0 else 0
        
        region_costs = []
        for r in range(self.num_regions):
            steps_to_run = work_steps_left
            if r != current_region:
                # Add overhead steps if we switch
                steps_to_run += self.overhead_in_steps
            
            trace = self.spot_traces[r]
            trace_len = len(trace)
            
            end_step = current_timestep + steps_to_run
            
            trace_slice = trace[current_timestep:min(end_step, trace_len)]
            
            num_spot_avail = sum(trace_slice)
            steps_in_slice = len(trace_slice)
            # Assume on-demand for any steps beyond the available trace data
            shortfall_steps = steps_to_run - steps_in_slice
            num_od_needed = (steps_in_slice - num_spot_avail) + shortfall_steps
            
            cost = (num_spot_avail * self.spot_cost_per_step +
                    num_od_needed * self.od_cost_per_step)
            region_costs.append(cost)

        best_region = region_costs.index(min(region_costs))
        
        if best_region != current_region:
            self.env.switch_region(best_region)
            # Update has_spot for the new region
            if current_timestep < len(self.spot_traces[best_region]):
                has_spot = bool(self.spot_traces[best_region][current_timestep])
            else:
                has_spot = False

        # 4. Cluster Type Selection in the chosen region
        slack = time_left - effective_work_left

        if has_spot:
            # Caution mode: if slack is low, use OD to avoid preemption risk
            caution_threshold = self.restart_overhead * 1.5
            if slack <= caution_threshold:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT
        else:
            # No spot. Decide between ON_DEMAND and NONE.
            # Find when spot is next available in the current (best) region.
            steps_to_wait = float('inf')
            region_trace = self.spot_traces[self.env.get_current_region()]
            trace_len = len(region_trace)
            if current_timestep + 1 < trace_len:
                try:
                    # Find the index of the next '1' in the rest of the trace
                    next_spot_in_slice = region_trace[current_timestep + 1:].index(1)
                    steps_to_wait = next_spot_in_slice + 1
                except ValueError:
                    # No more spot available in this region's trace
                    pass

            # If we can afford the time to wait, do so. Add a buffer to be safe.
            wait_buffer = self.restart_overhead
            if slack > (steps_to_wait * self.gap_seconds) + wait_buffer:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND