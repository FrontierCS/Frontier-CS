import json
import os
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

        self.region_scores = []
        spec_dir = os.path.dirname(os.path.abspath(spec_path))
        for trace_file in config["trace_files"]:
            full_trace_path = os.path.join(spec_dir, trace_file)
            with open(full_trace_path) as f:
                trace = json.load(f)

            if not trace:
                self.region_scores.append(0.0)
                continue

            avg_avail = sum(trace) / len(trace)

            streaks = []
            current_streak = 0
            for val in trace:
                if val == 1:
                    current_streak += 1
                else:
                    if current_streak > 0:
                        streaks.append(current_streak)
                    current_streak = 0
            if current_streak > 0:
                streaks.append(current_streak)

            avg_streak = sum(streaks) / len(streaks) if streaks else 0
            
            score = avg_avail * avg_streak
            self.region_scores.append(score)

        if not self.region_scores:
            self.best_region_idx = 0
        else:
            self.best_region_idx = max(
                range(len(self.region_scores)), key=self.region_scores.__getitem__
            )

        self.init_done = False
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
        if not self.init_done:
            self.init_done = True
            if self.env.get_current_region() != self.best_region_idx:
                self.env.switch_region(self.best_region_idx)
                return ClusterType.NONE

        remaining_work = self.task_duration - sum(self.task_done_time)

        if remaining_work <= 0:
            return ClusterType.NONE

        time_available = self.deadline - self.env.elapsed_seconds
        time_needed_on_demand = remaining_work + self.remaining_restart_overhead

        safety_buffer = 3 * self.restart_overhead
        if time_needed_on_demand + safety_buffer >= time_available:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            current_region = self.env.get_current_region()
            if current_region != self.best_region_idx:
                self.env.switch_region(self.best_region_idx)
                return ClusterType.NONE
            else:
                slack = time_available - time_needed_on_demand
                wait_threshold = self.env.gap_seconds + self.restart_overhead
                if slack > wait_threshold:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND