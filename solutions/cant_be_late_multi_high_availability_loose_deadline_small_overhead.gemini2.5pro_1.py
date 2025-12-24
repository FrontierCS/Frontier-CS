import json
from argparse import Namespace

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

        self.spot_traces = []
        try:
            for trace_file in config["trace_files"]:
                with open(trace_file) as f:
                    trace = [int(line.strip()) for line in f if line.strip()]
                    self.spot_traces.append(trace)
        except (IOError, ValueError):
            self.spot_traces = []

        if not self.spot_traces:
            self.consecutive_spot_counts = []
            return self

        num_regions = len(self.spot_traces)
        self.consecutive_spot_counts = []
        for r in range(num_regions):
            trace = self.spot_traces[r]
            trace_len = len(trace)
            counts = [0] * trace_len
            if trace_len > 0:
                if trace[trace_len - 1] == 1:
                    counts[trace_len - 1] = 1
                for t in range(trace_len - 2, -1, -1):
                    if trace[t] == 1:
                        counts[t] = 1 + counts[t + 1]
            self.consecutive_spot_counts.append(counts)
            
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
        remaining_work = self.task_duration - sum(self.task_done_time)

        if remaining_work <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time
        gap = self.env.gap_seconds

        safety_buffer = self.restart_overhead
        if time_to_deadline <= remaining_work + safety_buffer:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        current_step_idx = int(round(current_time / gap))

        best_switch_region = -1
        max_future_spot = 0

        if self.spot_traces:
            for r in range(num_regions):
                if r == current_region:
                    continue
                
                if r < len(self.spot_traces) and current_step_idx < len(self.spot_traces[r]):
                    if self.spot_traces[r][current_step_idx] == 1:
                        future_spot_steps = self.consecutive_spot_counts[r][current_step_idx]
                        if future_spot_steps > max_future_spot:
                            max_future_spot = future_spot_steps
                            best_switch_region = r

        if best_switch_region != -1:
            time_cost_of_switch = self.restart_overhead + gap
            slack = time_to_deadline - remaining_work

            is_slack_sufficient = slack > time_cost_of_switch
            is_switch_beneficial = (max_future_spot * gap) > time_cost_of_switch

            if is_slack_sufficient and is_switch_beneficial:
                self.env.switch_region(best_switch_region)
                return ClusterType.SPOT
        
        slack = time_to_deadline - remaining_work
        
        if slack > gap + self.restart_overhead:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
