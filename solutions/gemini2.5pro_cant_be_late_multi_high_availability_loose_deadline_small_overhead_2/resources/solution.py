import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "dp_lookahead_strategy"

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
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                self.traces.append(json.load(f))

        self.consecutive_availability = []
        for trace in self.traces:
            n_timesteps = len(trace)
            consecutive = [0] * n_timesteps
            if n_timesteps > 0:
                if trace[n_timesteps - 1]:
                    consecutive[n_timesteps - 1] = 1
                for t in range(n_timesteps - 2, -1, -1):
                    if trace[t]:
                        consecutive[t] = consecutive[t + 1] + 1
                    else:
                        consecutive[t] = 0
            self.consecutive_availability.append(consecutive)
        
        # With 24h duration and 48h deadline, initial slack is 24h.
        # This threshold determines when to switch to On-Demand during a long
        # spot outage, even with some slack remaining.
        self.procrastination_threshold_seconds = 6 * 3600.0

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
        remaining_work = self.task_duration - work_done

        if remaining_work <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_left = self.deadline - time_now
        
        time_needed_on_demand = self.remaining_restart_overhead + remaining_work

        # Panic mode: If time required to finish on On-Demand is greater than
        # or equal to time left, we must use On-Demand to avoid failure.
        if time_needed_on_demand >= time_left:
            return ClusterType.ON_DEMAND
        
        current_timestep = int(time_now / self.env.gap_seconds)
        num_regions = self.env.get_num_regions()

        # If current region has spot, use it.
        if has_spot:
            return ClusterType.SPOT

        # Current region has no spot. Find the best region to switch to.
        # Best is defined as having the longest consecutive spot availability from now.
        best_region_idx = -1
        max_consecutive_spot = 0
        
        for r_idx in range(num_regions):
            if current_timestep < len(self.consecutive_availability[r_idx]):
                consecutive_spot = self.consecutive_availability[r_idx][current_timestep]
                if consecutive_spot > max_consecutive_spot:
                    max_consecutive_spot = consecutive_spot
                    best_region_idx = r_idx

        # If a region with available spot is found, switch to it.
        if best_region_idx != -1:
            # Check if the switch overhead would put us in panic mode.
            time_needed_if_switch = self.restart_overhead + remaining_work
            if time_needed_if_switch >= time_left:
                return ClusterType.ON_DEMAND
            else:
                self.env.switch_region(best_region_idx)
                return ClusterType.SPOT

        # No spot available in any region. Decide between On-Demand and None.
        slack_time = time_left - time_needed_on_demand

        # If slack is too low, we must work.
        if slack_time < self.env.gap_seconds:
            return ClusterType.ON_DEMAND
            
        # If spot will be available next step in any region, wait.
        is_spot_available_next_step = False
        next_timestep = current_timestep + 1
        for r_idx in range(num_regions):
            if next_timestep < len(self.traces[r_idx]) and self.traces[r_idx][next_timestep]:
                is_spot_available_next_step = True
                break
        
        if is_spot_available_next_step:
            return ClusterType.NONE
        
        # Spot is not coming back soon. Decide based on slack threshold.
        if slack_time > self.procrastination_threshold_seconds:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
