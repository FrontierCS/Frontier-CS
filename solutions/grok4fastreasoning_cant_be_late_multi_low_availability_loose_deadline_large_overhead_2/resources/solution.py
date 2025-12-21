import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "greedy_spot_streak"

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

        # Load traces
        self.traces = []
        trace_files = config.get("trace_files", [])
        self.T = math.ceil(self.deadline / self.env.gap_seconds)
        for path in trace_files:
            with open(path, 'r') as tf:
                trace = json.load(tf)
            # Assume trace is list of bool; pad or truncate to T
            if len(trace) < self.T:
                trace.extend([False] * (self.T - len(trace)))
            else:
                trace = trace[:self.T]
            self.traces.append(trace)

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
        if self.env.elapsed_seconds >= self.deadline:
            return ClusterType.NONE

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        num_regions = self.env.get_num_regions()
        if current_step >= self.T:
            return ClusterType.ON_DEMAND

        # Find region with longest spot streak starting now
        max_streak = 0
        best_r = -1
        for r in range(num_regions):
            if current_step >= len(self.traces[r]) or not self.traces[r][current_step]:
                streak = 0
            else:
                streak = 1
                for t in range(current_step + 1, len(self.traces[r])):
                    if not self.traces[r][t]:
                        break
                    streak += 1
            if streak > max_streak:
                max_streak = streak
                best_r = r

        curr_r = self.env.get_current_region()
        if max_streak == 0:
            # No spot available anywhere, use ON_DEMAND, no switch
            return ClusterType.ON_DEMAND
        else:
            # Switch to best if not current
            if best_r != curr_r:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
