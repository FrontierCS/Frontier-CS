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

        self.traces = []
        try:
            if "trace_files" in config:
                for trace_file in config["trace_files"]:
                    with open(trace_file) as f:
                        self.traces.append(json.load(f))
        except (IOError, json.JSONDecodeError):
            self.traces = []

        self.streaks = []
        if self.traces and self.traces[0]:
            num_regions = len(self.traces)
            trace_len = len(self.traces[0])
            self.streaks = [[0] * trace_len for _ in range(num_regions)]
            
            for r in range(num_regions):
                if self.traces[r][trace_len - 1]:
                    self.streaks[r][trace_len - 1] = 1
                for t in range(trace_len - 2, -1, -1):
                    if self.traces[r][t]:
                        self.streaks[r][t] = 1 + self.streaks[r][t+1]
        
        self.buffer_factor = 2.0
        
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

        elapsed_time = self.env.elapsed_seconds
        time_left = self.deadline - elapsed_time

        if time_left <= remaining_work:
            return ClusterType.ON_DEMAND 

        safety_buffer = self.buffer_factor * self.restart_overhead
        time_needed_if_panic = self.restart_overhead + remaining_work + safety_buffer

        if time_needed_if_panic >= time_left:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        
        # No spot in the current region, so look for alternatives.
        current_step = int(elapsed_time // self.env.gap_seconds)
        
        num_regions = self.env.get_num_regions()
        trace_len = 0
        if self.streaks and self.streaks[0]:
            trace_len = len(self.streaks[0])

        best_region_idx = -1
        max_streak = 0

        # Find the region with the longest continuous spot availability from now.
        for r in range(num_regions):
            streak = 0
            if current_step < trace_len:
                streak = self.streaks[r][current_step]
            
            if streak > max_streak:
                max_streak = streak
                best_region_idx = r
        
        if max_streak > 0:
            # A region with spot is available. Switch to it.
            if self.env.get_current_region() != best_region_idx:
                self.env.switch_region(best_region_idx)
            return ClusterType.SPOT
        else:
            # No spot available in any region. Decide between ON_DEMAND and NONE.
            # We wait (NONE) only if we can afford the time loss.
            time_left_after_wait = time_left - self.env.gap_seconds
            if time_needed_if_panic >= time_left_after_wait:
                # Waiting is too risky. Must make progress with On-Demand.
                return ClusterType.ON_DEMAND
            else:
                # It's safe to wait for a spot instance to become available.
                return ClusterType.NONE